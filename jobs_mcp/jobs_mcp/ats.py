"""Adapters that pull jobs from company career sections.

Preferred path: the public job-board APIs that most careers pages are built on
(Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee). These are
published by the vendors for exactly this purpose and are far more reliable than
scraping HTML. Fallback: schema.org JobPosting JSON-LD on the careers page and
its linked job pages (what Google for Jobs reads).
"""
import asyncio, datetime as dt, json, re
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from .text import html_to_text

UA = "Mozilla/5.0 (compatible; jobs-mcp/0.1; +career-page-indexer)"
TIMEOUT = httpx.Timeout(30.0)

def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers={"User-Agent": UA, "Accept": "application/json, text/html"},
                             timeout=TIMEOUT, follow_redirects=True)

# ---------------------------------------------------------------- detection
PATTERNS = [
    ("greenhouse", r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)"),
    ("greenhouse", r"greenhouse\.io/embed/job_board(?:/js)?\?for=([A-Za-z0-9_-]+)"),
    ("greenhouse", r"boards-api\.greenhouse\.io/v1/boards/([A-Za-z0-9_-]+)"),
    ("lever", r"jobs\.(?:eu\.)?lever\.co/([A-Za-z0-9_.-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)"),
    ("workable", r"apply\.workable\.com/([A-Za-z0-9_-]+)"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)"),
    ("recruitee", r"([A-Za-z0-9_-]+)\.recruitee\.com"),
    ("personio", r"([a-z0-9-]+)\.jobs\.personio\.(?:de|com)"),
    ("breezy", r"([a-z0-9-]+)\.breezy\.hr"),
    ("workday", r"([a-z0-9-]+\.wd\d+\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?[A-Za-z0-9_-]+)"),
]
SKIP_TOKENS = {"embed", "api", "v1", "j", "jobs", "widget", "static", "assets", "www", "app", "help", "support", "careers"}

def detect_from_text(text: str):
    for ats, pat in PATTERNS:
        for m in re.finditer(pat, text):
            tok = m.group(1)
            if tok.lower() not in SKIP_TOKENS:
                return ats, tok
    return None

async def detect(careers_url: str) -> dict:
    """Work out which ATS powers a careers page. Checks the URL, then the page HTML
    (embedded boards, apply links), else falls back to JSON-LD scraping."""
    hit = detect_from_text(careers_url)
    if hit:
        return {"ats": hit[0], "token": hit[1]}
    async with client() as c:
        r = await c.get(careers_url)
        body = r.text
        hit = detect_from_text(str(r.url)) or detect_from_text(body)
    if hit:
        return {"ats": hit[0], "token": hit[1]}
    return {"ats": "jsonld", "token": None}

# ---------------------------------------------------------------- helpers
def _iso(ms_or_str):
    if ms_or_str is None:
        return None
    if isinstance(ms_or_str, (int, float)):
        return dt.datetime.fromtimestamp(ms_or_str / 1000, dt.timezone.utc).isoformat()
    return str(ms_or_str)

def _remote_from(*vals) -> bool | None:
    for v in vals:
        if v is None:
            continue
        if isinstance(v, bool):
            return v
        s = str(v).lower()
        if "remote" in s:
            return True
        if s in ("onsite", "on-site", "hybrid"):
            return False
    return None

# ---------------------------------------------------------------- adapters
async def fetch_greenhouse(c, token, limit):
    r = await c.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", params={"content": "true"})
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", [])[:limit]:
        loc = (j.get("location") or {}).get("name")
        out.append({
            "id": f"greenhouse:{token}:{j['id']}", "title": j.get("title"),
            "department": ", ".join(d["name"] for d in j.get("departments") or [] if d.get("name")) or None,
            "location": loc, "remote": _remote_from(loc), "url": j.get("absolute_url"),
            "apply_url": j.get("absolute_url"), "description": html_to_text(j.get("content")),
            "posted_at": j.get("first_published") or j.get("updated_at")})
    return out

async def fetch_lever(c, token, limit):
    base = "https://api.lever.co/v0/postings"
    r = await c.get(f"{base}/{token}", params={"mode": "json"})
    if r.status_code == 404:  # EU-hosted Lever accounts
        r = await c.get(f"https://api.eu.lever.co/v0/postings/{token}", params={"mode": "json"})
    r.raise_for_status()
    out = []
    for j in r.json()[:limit]:
        cat = j.get("categories") or {}
        parts = [j.get("descriptionPlain") or ""]
        for l in j.get("lists") or []:
            parts.append(f"{l.get('text','')}\n{html_to_text(l.get('content'))}")
        parts.append(j.get("additionalPlain") or "")
        sal = j.get("salaryRange") or {}
        out.append({
            "id": f"lever:{token}:{j['id']}", "title": j.get("text"),
            "department": cat.get("team") or cat.get("department"), "location": cat.get("location"),
            "country": j.get("country"), "remote": _remote_from(j.get("workplaceType"), cat.get("location")),
            "employment_type": cat.get("commitment"), "url": j.get("hostedUrl"), "apply_url": j.get("applyUrl"),
            "description": "\n\n".join(p for p in parts if p).strip(),
            "salary": f"{sal.get('currency','')} {sal.get('min')}-{sal.get('max')} {sal.get('interval','')}".strip() if sal else None,
            "posted_at": _iso(j.get("createdAt"))})
    return out

async def fetch_ashby(c, token, limit):
    r = await c.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}", params={"includeCompensation": "true"})
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", [])[:limit]:
        if j.get("isListed") is False:
            continue
        addr = ((j.get("address") or {}).get("postalAddress") or {})
        comp = (j.get("compensation") or {}).get("compensationTierSummary")
        out.append({
            "id": f"ashby:{token}:{j['id']}", "title": j.get("title"),
            "department": j.get("department") or j.get("team"), "location": j.get("location"),
            "country": addr.get("addressCountry"),
            "remote": j.get("isRemote") if j.get("isRemote") is not None else _remote_from(j.get("workplaceType")),
            "employment_type": j.get("employmentType"), "url": j.get("jobUrl"), "apply_url": j.get("applyUrl"),
            "description": j.get("descriptionPlain") or html_to_text(j.get("descriptionHtml")),
            "salary": comp, "posted_at": j.get("publishedAt")})
    return out

async def fetch_workable(c, token, limit):
    r = await c.get(f"https://apply.workable.com/api/v1/widget/accounts/{token}", params={"details": "true"})
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", [])[:limit]:
        loc = ", ".join(x for x in [j.get("city"), j.get("state"), j.get("country")] if x)
        out.append({
            "id": f"workable:{token}:{j.get('shortcode')}", "title": j.get("title"),
            "department": j.get("department"), "location": loc, "country": j.get("country"),
            "remote": j.get("telecommuting"), "employment_type": j.get("employment_type"),
            "url": j.get("url") or j.get("shortlink"), "apply_url": j.get("application_url"),
            "description": html_to_text(j.get("description")), "posted_at": j.get("published_on")})
    return out

async def fetch_smartrecruiters(c, token, limit):
    out, offset = [], 0
    while len(out) < limit:
        r = await c.get(f"https://api.smartrecruiters.com/v1/companies/{token}/postings",
                        params={"limit": 100, "offset": offset})
        r.raise_for_status()
        d = r.json()
        items = d.get("content", [])
        for j in items:
            loc = j.get("location") or {}
            out.append({
                "id": f"smartrecruiters:{token}:{j['id']}", "title": j.get("name"),
                "department": (j.get("department") or {}).get("label") or (j.get("function") or {}).get("label"),
                "location": loc.get("fullLocation"), "country": (loc.get("country") or "").upper() or None,
                "remote": loc.get("remote"), "employment_type": (j.get("typeOfEmployment") or {}).get("label"),
                "url": f"https://jobs.smartrecruiters.com/{token}/{j['id']}", "apply_url": None,
                "description": "",  # fetched on demand by fetch_detail (list endpoint omits it)
                "posted_at": j.get("releasedDate")})
        offset += len(items)
        if not items or offset >= d.get("totalFound", 0):
            break
    return out[:limit]

def _wd_parts(token):
    host, *rest = token.split("/")
    site = [r for r in rest if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", r)][0]
    return host, host.split(".")[0], site

def _wd_age(posted: str | None):
    if not posted: return None
    s = posted.lower()
    days = 0 if ("today" in s) else 1 if "yesterday" in s else None
    m = re.search(r"(\d+)\+?\s*day", s)
    if m: days = int(m.group(1))
    if days is None: return None
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).date().isoformat()

async def fetch_workday(c, token, limit):
    host, tenant, site = _wd_parts(token)
    api = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    sem = asyncio.Semaphore(5)
    async def page(offset):
        async with sem:
            for attempt in range(3):
                try:
                    r = await c.post(api, json={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""})
                    r.raise_for_status()
                    return r.json()
                except httpx.HTTPError:
                    if attempt == 2: raise
                    await asyncio.sleep(2 * (attempt + 1))
    first = await page(0)
    total = min(first.get("total", 0), limit)  # Workday reports total only on page 1 (capped at 2000)
    pages = [first] + await asyncio.gather(*(page(o) for o in range(20, total, 20)))
    out, seen = [], set()
    for d in pages:
        for j in d.get("jobPostings", []):
            path = j.get("externalPath", "")
            jid = f"workday:{token}:{path.rsplit('_', 1)[-1] or path}"
            if jid in seen: continue
            seen.add(jid)
            loc = j.get("locationsText")
            if not loc or re.fullmatch(r"\d+ Locations", loc):  # Workday hides multi-location; use primary from URL
                seg = path.split("/job/", 1)[-1].split("/", 1)[0]
                loc = seg.replace("-", " ") + (f" (+{loc.split()[0]} locations)" if loc else "")
            out.append({"id": jid, "title": j.get("title"), "location": loc,
                        "remote": _remote_from(j.get("remoteType"), j.get("locationsText")),
                        "url": f"https://{host}/{site}{path}", "apply_url": f"https://{host}/{site}{path}/apply",
                        "description": "", "posted_at": _wd_age(j.get("postedOn"))})
    return out[:limit]

async def fetch_personio(c, token, limit):
    import xml.etree.ElementTree as ET
    r = await c.get(f"https://{token}.jobs.personio.de/xml")
    r.raise_for_status()
    out = []
    for p in ET.fromstring(r.content).findall("position")[:limit]:
        g = lambda k: (p.findtext(k) or "").strip() or None
        desc = "\n\n".join(f"{d.findtext('name') or ''}\n{html_to_text(d.findtext('value'))}" for d in p.iter("jobDescription"))
        out.append({"id": f"personio:{token}:{g('id')}", "title": g("name"), "department": g("department"),
                    "location": g("office"), "remote": _remote_from(g("office")), "employment_type": g("employmentType"),
                    "url": f"https://{token}.jobs.personio.de/job/{g('id')}", "apply_url": f"https://{token}.jobs.personio.de/job/{g('id')}#apply",
                    "description": desc.strip(), "posted_at": g("createdAt")})
    return out

async def fetch_breezy(c, token, limit):
    r = await c.get(f"https://{token}.breezy.hr/json")
    r.raise_for_status()
    out = []
    for j in r.json()[:limit]:
        loc = j.get("location") or {}
        out.append({"id": f"breezy:{token}:{j['id']}", "title": j.get("name"), "department": j.get("department"),
                    "location": loc.get("name"), "country": ((loc.get("country") or {}).get("id") or "").upper() or None,
                    "remote": loc.get("is_remote"), "employment_type": (j.get("type") or {}).get("name"),
                    "url": j.get("url"), "apply_url": j.get("url"), "description": "",
                    "salary": j.get("salary") or None, "posted_at": j.get("published_date")})
    return out

async def fetch_recruitee(c, token, limit):
    r = await c.get(f"https://{token}.recruitee.com/api/offers/")
    r.raise_for_status()
    out = []
    for j in r.json().get("offers", [])[:limit]:
        if j.get("status") not in (None, "published"):
            continue
        sal = j.get("salary") or {}
        out.append({
            "id": f"recruitee:{token}:{j['id']}", "title": j.get("title"), "department": j.get("department"),
            "location": j.get("location"), "country": j.get("country_code") or j.get("country"),
            "remote": j.get("remote"), "employment_type": j.get("employment_type_code"),
            "url": j.get("careers_url"), "apply_url": j.get("careers_apply_url"),
            "description": html_to_text((j.get("description") or "") + (j.get("requirements") or "")),
            "salary": f"{sal.get('currency','')} {sal.get('min')}-{sal.get('max')} {sal.get('period','')}".strip() if sal.get("min") else None,
            "posted_at": j.get("published_at"),
            "contact": {"email": j["mailbox_email"], "source": "recruitee_mailbox"} if j.get("mailbox_email") else None})
    return out

# ---- generic fallback: schema.org JobPosting JSON-LD
JOB_LINK_HINT = re.compile(r"/(job|jobs|career|careers|position|positions|opening|openings|vacanc|role)s?/", re.I)

def _jsonld_postings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                t = d.get("@type")
                if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                    found.append(d)
                stack.extend(v for v in d.values() if isinstance(v, (list, dict)))
            elif isinstance(d, list):
                stack.extend(d)
    return found

def _norm_jsonld(p: dict, url: str, key: str) -> dict:
    locs = p.get("jobLocation") or []
    locs = locs if isinstance(locs, list) else [locs]
    names, country = [], None
    for l in locs:
        a = (l or {}).get("address") or {}
        if isinstance(a, dict):
            names.append(", ".join(x for x in [a.get("addressLocality"), a.get("addressRegion"), a.get("addressCountry") if isinstance(a.get("addressCountry"), str) else None] if x))
            country = country or (a.get("addressCountry") if isinstance(a.get("addressCountry"), str) else (a.get("addressCountry") or {}).get("name"))
    org = p.get("hiringOrganization") or {}
    ident = p.get("identifier")
    jid = (ident.get("value") if isinstance(ident, dict) else ident) or p.get("url") or url
    return {
        "id": f"jsonld:{key}:{jid}", "title": p.get("title"), "location": "; ".join(n for n in names if n) or None,
        "country": country, "remote": True if p.get("jobLocationType") == "TELECOMMUTE" else None,
        "employment_type": p.get("employmentType") if isinstance(p.get("employmentType"), str) else ", ".join(p.get("employmentType") or []) or None,
        "url": p.get("url") or url, "apply_url": p.get("url") or url,
        "description": html_to_text(p.get("description")), "posted_at": p.get("datePosted"),
        "valid_through": p.get("validThrough"), "company_name": org.get("name") if isinstance(org, dict) else None}

async def fetch_jsonld(c, careers_url, limit, max_pages=40):
    r = await c.get(careers_url)
    r.raise_for_status()
    key = urlparse(careers_url).netloc
    posts = [_norm_jsonld(p, careers_url, key) for p in _jsonld_postings(r.text)]
    if not posts:  # listing page has no JSON-LD: follow job-looking links on the same site
        soup = BeautifulSoup(r.text, "html.parser")
        host = urlparse(str(r.url)).netloc
        links = []
        for a in soup.find_all("a", href=True):
            u = urljoin(str(r.url), a["href"]).split("#")[0]
            if urlparse(u).netloc == host and JOB_LINK_HINT.search(u) and u != str(r.url) and u not in links:
                links.append(u)
        sem = asyncio.Semaphore(5)
        async def one(u):
            async with sem:
                try:
                    rr = await c.get(u)
                    return [_norm_jsonld(p, u, key) for p in _jsonld_postings(rr.text)]
                except Exception:
                    return []
        for batch in await asyncio.gather(*(one(u) for u in links[:max_pages])):
            posts.extend(batch)
    seen, out = set(), []
    for p in posts:
        if p["id"] not in seen:
            seen.add(p["id"]); out.append(p)
    return out[:limit]

ADAPTERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby,
            "workable": fetch_workable, "workday": fetch_workday,
            "personio": fetch_personio, "breezy": fetch_breezy, "smartrecruiters": fetch_smartrecruiters, "recruitee": fetch_recruitee}

async def fetch_company_jobs(company: dict, limit: int = 500) -> list[dict]:
    async with client() as c:
        if company["ats"] == "jsonld":
            return await fetch_jsonld(c, company["careers_url"], limit)
        return await ADAPTERS[company["ats"]](c, company["token"], limit)

async def fetch_detail(job_id: str, url: str | None = None) -> dict:
    """Fill in fields the list endpoints omit (SmartRecruiters and Workday descriptions)."""
    ats, token, jid = job_id.split(":", 2)
    if ats == "workday" and url:
        host, tenant, site = _wd_parts(token)
        path = url.split(f"/{site}", 1)[1]
        async with client() as c:
            r = await c.get(f"https://{host}/wday/cxs/{tenant}/{site}{path}")
            r.raise_for_status()
            info = r.json().get("jobPostingInfo", {})
        return {"description": html_to_text(info.get("jobDescription")), "url": info.get("externalUrl") or url}
    if ats != "smartrecruiters":
        return {}
    async with client() as c:
        r = await c.get(f"https://api.smartrecruiters.com/v1/companies/{token}/postings/{jid}")
        r.raise_for_status()
        d = r.json()
    secs = ((d.get("jobAd") or {}).get("sections") or {})
    text = "\n\n".join(f"{(s or {}).get('title','')}\n{html_to_text((s or {}).get('text'))}" for s in secs.values() if s)
    creator = (d.get("creator") or {}).get("name")
    return {"description": text.strip(), "apply_url": d.get("applyUrl"), "url": d.get("postingUrl"),
            "contact": {"name": creator, "source": "smartrecruiters_posting_creator"} if creator else None}
