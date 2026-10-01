"""Step 3 – validate each discovered board (does it exist, how many open jobs, display
name), then register live ones as companies the MCP server syncs and searches."""
import asyncio, sys, time
import httpx
from jobs_mcp import store
from jobs_mcp.ats import UA, _wd_parts

def careers_url(ats, token):
    return {"greenhouse": f"https://boards.greenhouse.io/{token}", "lever": f"https://jobs.lever.co/{token}",
            "ashby": f"https://jobs.ashbyhq.com/{token}", "workable": f"https://apply.workable.com/{token}",
            "smartrecruiters": f"https://jobs.smartrecruiters.com/{token}", "recruitee": f"https://{token}.recruitee.com",
            "personio": f"https://{token}.jobs.personio.de", "breezy": f"https://{token}.breezy.hr",
            "workday": f"https://{token}", "jsonld": token}[ats]

async def probe(c, ats, token):
    """Return (job_count, display_name). Raises on dead boards."""
    if ats == "greenhouse":
        r = await c.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"); r.raise_for_status()
        n = len(r.json().get("jobs", []))
        meta = await c.get(f"https://boards-api.greenhouse.io/v1/boards/{token}")
        return n, (meta.json().get("name") if meta.status_code == 200 else None)
    if ats == "lever":
        r = await c.get(f"https://api.lever.co/v0/postings/{token}", params={"mode": "json", "limit": 1000})
        if r.status_code == 404:
            r = await c.get(f"https://api.eu.lever.co/v0/postings/{token}", params={"mode": "json"})
        r.raise_for_status(); return len(r.json()), None
    if ats == "ashby":
        r = await c.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}"); r.raise_for_status()
        return len(r.json().get("jobs", [])), None
    if ats == "workable":
        r = await c.get(f"https://apply.workable.com/api/v1/widget/accounts/{token}"); r.raise_for_status()
        d = r.json(); return len(d.get("jobs", [])), d.get("name")
    if ats == "smartrecruiters":
        r = await c.get(f"https://api.smartrecruiters.com/v1/companies/{token}/postings", params={"limit": 1}); r.raise_for_status()
        d = r.json(); items = d.get("content") or [{}]
        return d.get("totalFound", 0), (items[0].get("company") or {}).get("name")
    if ats == "recruitee":
        r = await c.get(f"https://{token}.recruitee.com/api/offers/"); r.raise_for_status()
        offers = r.json().get("offers", []); return len(offers), (offers[0].get("company_name") if offers else None)
    if ats == "personio":
        r = await c.get(f"https://{token}.jobs.personio.de/xml"); r.raise_for_status()
        import xml.etree.ElementTree as ET
        pos = ET.fromstring(r.content).findall("position")
        return len(pos), (pos[0].findtext("subcompany") if pos else None)
    if ats == "breezy":
        r = await c.get(f"https://{token}.breezy.hr/json"); r.raise_for_status(); return len(r.json()), None
    if ats == "workday":
        host, tenant, site = _wd_parts(token)
        r = await c.post(f"https://{host}/wday/cxs/{tenant}/{site}/jobs", json={"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
        r.raise_for_status(); return r.json().get("total", 0), None
    if ats == "jsonld":
        return -1, None  # counted at sync time
    raise ValueError(f"unsupported ats {ats}")

def pretty(token: str) -> str:
    t = token.split(".")[0] if "myworkdayjobs" in token else token
    return t.replace("-", " ").replace("_", " ").title()

async def run(con, statuses=("new",), recheck_days=7, concurrency=25, limit=100000):
    cutoff = time.time() - recheck_days * 86400
    q = f"""SELECT id, ats, token FROM boards WHERE status IN ({','.join('?'*len(statuses))})
            OR (status IN ('active','empty') AND IFNULL(last_checked,0) < ?) LIMIT ?"""
    rows = con.execute(q, (*statuses, cutoff, limit)).fetchall()
    print(f"  validating {len(rows):,} boards", file=sys.stderr)
    sem = asyncio.Semaphore(concurrency)
    tally = {}
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=30, follow_redirects=True) as c:
        async def one(r):
            async with sem:
                for attempt in range(3):
                    try:
                        n, name = await probe(c, r["ats"], r["token"])
                        return r, ("active" if n != 0 else "empty"), n, name, None
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 429:
                            await asyncio.sleep(5 * (attempt + 1)); continue
                        return r, "dead", 0, None, f"HTTP {e.response.status_code}"
                    except Exception as e:
                        err = str(e)[:200]; await asyncio.sleep(2)
                return r, "error", None, None, err
        done = 0
        for fut in asyncio.as_completed([one(r) for r in rows]):
            r, status, n, name, err = await fut
            done += 1; tally[status] = tally.get(status, 0) + 1
            con.execute("UPDATE boards SET status=?, job_count=?, board_name=COALESCE(?,board_name), last_checked=?, error=? WHERE id=?",
                        (status, n, name, time.time(), err, r["id"]))
            if status == "active":
                cid = store.upsert_company(con, name=(name or pretty(r["token"])).strip(), ats=r["ats"],
                                           token=None if r["ats"] == "jsonld" else r["token"],
                                           careers_url=careers_url(r["ats"], r["token"]))
                con.execute("UPDATE boards SET company_id=? WHERE id=?", (cid, r["id"]))
            if done % 250 == 0:
                con.commit(); print(f"\r  {done:,}/{len(rows):,} {tally}", end="", file=sys.stderr)
    con.commit()
    print(file=sys.stderr)
    return tally

def link(con):
    """Attach live boards to registry companies (HQ country, legal name) by domain, then normalised name."""
    from .db import norm_name
    n = 0
    for b in con.execute("""SELECT b.id, b.discovered_via, b.board_name, b.token, b.company_id FROM boards b
                            WHERE b.status='active' AND b.universe_id IS NULL""").fetchall():
        u = None
        if (b["discovered_via"] or "").startswith("domain:"):
            u = con.execute("SELECT id, country, domain FROM universe WHERE domain=? LIMIT 1", (b["discovered_via"][7:],)).fetchone()
        if not u:
            key = norm_name(b["board_name"] or pretty(b["token"]))
            if len(key) >= 3:
                u = con.execute("""SELECT id, country, domain FROM universe WHERE norm_name=?
                                   ORDER BY (domain IS NOT NULL) DESC, (source='wikidata') DESC LIMIT 1""", (key,)).fetchone()
        if u:
            con.execute("UPDATE boards SET universe_id=? WHERE id=?", (u["id"], b["id"]))
            con.execute("UPDATE companies SET country=COALESCE(country,?), domain=COALESCE(domain,?) WHERE id=?",
                        (u["country"], u["domain"], b["company_id"]))
            n += 1
    con.commit()
    return n
