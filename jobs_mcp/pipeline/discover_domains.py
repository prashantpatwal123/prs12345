"""Step 2b – forward discovery: for companies in the universe that have a website,
open the homepage and common careers paths, and detect which job board they use.
Catches employers the crawl missed, and custom careers pages (kept as JSON-LD boards)."""
import asyncio, re, sys, time
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
from jobs_mcp.ats import detect_from_text, UA, _jsonld_postings

PATHS = ["", "/careers", "/jobs", "/careers/", "/en/careers", "/about/careers", "/join-us", "/work-with-us"]
SUBS = ["careers", "jobs"]
CAREER_LINK = re.compile(r"career|jobs|join[- ]?us|work[- ]with[- ]us|vacanc|openings|hiring|karriere|empleo|emplois|carriere", re.I)

async def scan_domain(c, domain: str) -> dict:
    tried = []
    urls = [f"https://{domain}{p}" for p in PATHS] + [f"https://{s}.{domain}" for s in SUBS]
    for u in urls:
        try:
            r = await c.get(u)
        except httpx.HTTPError:
            continue
        if r.status_code >= 400:
            continue
        tried.append(str(r.url))
        hit = detect_from_text(str(r.url)) or detect_from_text(r.text)
        if hit:
            return {"ats": hit[0], "token": hit[1], "careers_url": str(r.url), "result": "ats"}
        if u == urls[0]:  # homepage: follow the careers link it actually shows
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                if CAREER_LINK.search(a.get_text(" ") + " " + a["href"]):
                    link = urljoin(str(r.url), a["href"])
                    hit = detect_from_text(link)
                    if hit:
                        return {"ats": hit[0], "token": hit[1], "careers_url": link, "result": "ats"}
                    if link not in urls:
                        urls.insert(1, link)
                    break
        if _jsonld_postings(r.text):
            return {"ats": "jsonld", "token": None, "careers_url": str(r.url), "result": "jsonld"}
    return {"ats": None, "token": None, "careers_url": None, "result": "none" if tried else "unreachable"}

async def run(con, limit: int = 5000, concurrency: int = 40, recheck_days: int = 30):
    cutoff = time.time() - recheck_days * 86400
    domains = [r[0] for r in con.execute("""SELECT DISTINCT u.domain FROM universe u LEFT JOIN domain_scan d ON d.domain=u.domain
        WHERE u.domain IS NOT NULL AND IFNULL(u.status,'ACTIVE') NOT IN ('DISSOLVED','RETIRED','LAPSED')
        AND (d.domain IS NULL OR d.checked_at < ?) LIMIT ?""", (cutoff, limit))]
    print(f"  scanning {len(domains):,} domains", file=sys.stderr)
    sem = asyncio.Semaphore(concurrency)
    counts = {}
    async with httpx.AsyncClient(headers={"User-Agent": UA}, timeout=httpx.Timeout(15.0), follow_redirects=True,
                                 limits=httpx.Limits(max_connections=concurrency)) as c:
        async def one(d):
            async with sem:
                try:
                    res = await asyncio.wait_for(scan_domain(c, d), 90)
                except Exception:
                    res = {"ats": None, "token": None, "careers_url": None, "result": "error"}
                return d, res
        done = 0
        for fut in asyncio.as_completed([one(d) for d in domains]):
            d, res = await fut
            done += 1
            counts[res["result"]] = counts.get(res["result"], 0) + 1
            con.execute("INSERT OR REPLACE INTO domain_scan VALUES (?,?,?,?,?,?)",
                        (d, time.time(), res["careers_url"], res["ats"], res["token"], res["result"]))
            if res["ats"]:
                token = res["token"] if res["ats"] != "jsonld" else res["careers_url"]
                con.execute("INSERT OR IGNORE INTO boards(ats, token, discovered_via, first_found) VALUES (?,?,?,?)",
                            (res["ats"], token, f"domain:{d}", time.time()))
            if done % 200 == 0:
                con.commit()
                print(f"\r  {done:,}/{len(domains):,} {counts}", end="", file=sys.stderr)
    con.commit()
    print(file=sys.stderr)
    return counts
