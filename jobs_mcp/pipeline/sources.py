"""Step 1a – company universe from free, open registries.

gleif     Global LEI register: ~3.4M legal entities in 200+ countries, active and lapsed/retired
          (so it covers companies that existed, not just current ones). No websites.
wikidata  Companies with an official website, by country. Gives the name->domain link
          that the career-page scan needs.
sec       US SEC filers (CIK, ticker).
uk        UK Companies House basic company data (~5M live companies). Large download.
"""
import csv, io, json, time, zipfile, re, sys
import httpx
from .db import CACHE, norm_name, norm_domain

UA = {"User-Agent": "jobs-mcp-pipeline/0.1 (company dataset builder; set JOBS_MCP_CONTACT)"}
BATCH = 5000

def _download(url: str, dest, headers=None):
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, headers=headers or UA, timeout=None, follow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0)); done = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk); done += len(chunk)
                if total: print(f"\r  downloading {dest.name}: {done/total:5.1%}", end="", file=sys.stderr)
    print(file=sys.stderr)
    tmp.rename(dest)
    return dest

def _insert(con, rows):
    con.executemany("""INSERT INTO universe(source, source_id, name, norm_name, country, domain, status, category, extra)
                       VALUES (?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(source, source_id) DO UPDATE SET name=excluded.name, norm_name=excluded.norm_name,
                         country=excluded.country, domain=COALESCE(excluded.domain, universe.domain),
                         status=excluded.status, category=excluded.category""", rows)
    con.commit()

# ------------------------------------------------------------------ GLEIF
def load_gleif(con, include_inactive=True):
    meta = httpx.get("https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2/latest", timeout=60).json()
    url = meta["data"]["full_file"]["csv"]["url"]
    path = _download(url, CACHE / url.rsplit("/", 1)[-1])
    n, batch = 0, []
    with zipfile.ZipFile(path) as z:
        name = [x for x in z.namelist() if x.endswith(".csv")][0]
        with z.open(name) as f:
            for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
                status = row.get("Entity.EntityStatus")
                if not include_inactive and status != "ACTIVE":
                    continue
                if row.get("Entity.EntityCategory") in ("FUND",):  # investment funds aren't employers
                    continue
                nm = row.get("Entity.LegalName") or ""
                country = row.get("Entity.HeadquartersAddress.Country") or row.get("Entity.LegalAddress.Country")
                batch.append(("gleif", row["LEI"], nm, norm_name(nm), country, None, status,
                              row.get("Entity.EntityCategory"), None))
                if len(batch) >= BATCH:
                    _insert(con, batch); n += len(batch); batch = []
                    print(f"\r  gleif rows: {n:,}", end="", file=sys.stderr)
    _insert(con, batch); n += len(batch)
    print(file=sys.stderr)
    return n

# ------------------------------------------------------------------ Wikidata
TYPES = "wd:Q4830453 wd:Q783794 wd:Q6881511 wd:Q891723 wd:Q1589009 wd:Q658255 wd:Q167037 wd:Q778575 wd:Q2085381 wd:Q1631111 wd:Q21980538"
WD_Q = """SELECT ?c ?cLabel ?w ?cc ?dissolved WHERE {
  VALUES ?t { %s } ?c wdt:P31 ?t; wdt:P856 ?w; wdt:P17 ?country. ?country wdt:P297 "%s".
  BIND("%s" AS ?cc) OPTIONAL { ?c wdt:P576 ?dissolved }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". } } LIMIT %d OFFSET %d"""

def _countries():
    q = 'SELECT DISTINCT ?code WHERE { ?c wdt:P297 ?code }'
    r = httpx.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, headers=UA, timeout=120)
    return sorted({b["code"]["value"] for b in r.json()["results"]["bindings"]})

def load_wikidata(con, countries=None, page=10000):
    countries = countries or _countries()
    total = 0
    with httpx.Client(headers={**UA, "Accept": "application/sparql-results+json"}, timeout=180) as c:
        for cc in countries:
            off = 0
            while True:
                for attempt in range(4):
                    try:
                        r = c.get("https://query.wikidata.org/sparql", params={"query": WD_Q % (TYPES, cc, cc, page, off)})
                        if r.status_code == 429:
                            time.sleep(int(r.headers.get("retry-after", 30))); continue
                        r.raise_for_status(); break
                    except httpx.HTTPError:
                        time.sleep(10 * (attempt + 1))
                else:
                    print(f"  wikidata {cc}: gave up at offset {off}", file=sys.stderr); break
                rows = r.json()["results"]["bindings"]
                batch = []
                for b in rows:
                    qid = b["c"]["value"].rsplit("/", 1)[-1]
                    nm = b.get("cLabel", {}).get("value", qid)
                    batch.append(("wikidata", qid, nm, norm_name(nm), cc, norm_domain(b["w"]["value"]),
                                  "DISSOLVED" if b.get("dissolved") else "ACTIVE", None, None))
                _insert(con, batch); total += len(batch)
                print(f"\r  wikidata {cc}: {off + len(rows):,} (total {total:,})   ", end="", file=sys.stderr)
                if len(rows) < page: break
                off += page
                time.sleep(1)
    print(file=sys.stderr)
    return total

# ------------------------------------------------------------------ SEC
def load_sec(con):
    r = httpx.get("https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": "jobs-mcp-pipeline admin@example.com"}, timeout=60)
    rows = [("sec", str(v["cik_str"]), v["title"], norm_name(v["title"]), "US", None, "ACTIVE", "LISTED", json.dumps({"ticker": v["ticker"]}))
            for v in r.json().values()]
    _insert(con, rows)
    return len(rows)

# ------------------------------------------------------------------ UK Companies House
def load_uk(con):
    page = httpx.get("https://download.companieshouse.gov.uk/en_output.html", timeout=60).text
    fn = re.search(r'href="(BasicCompanyDataAsOneFile-[\d-]+\.zip)"', page).group(1)
    path = _download(f"https://download.companieshouse.gov.uk/{fn}", CACHE / fn)
    n, batch = 0, []
    with zipfile.ZipFile(path) as z, z.open(z.namelist()[0]) as f:
        rd = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
        hdr = [h.strip() for h in next(rd)]
        ix = {h: i for i, h in enumerate(hdr)}
        for row in rd:
            nm = row[ix["CompanyName"]]
            batch.append(("uk", row[ix["CompanyNumber"]], nm, norm_name(nm), "GB", None,
                          row[ix["CompanyStatus"]], row[ix["CompanyCategory"]], None))
            if len(batch) >= BATCH:
                _insert(con, batch); n += len(batch); batch = []
                print(f"\r  uk rows: {n:,}", end="", file=sys.stderr)
    _insert(con, batch)
    print(file=sys.stderr)
    return n + len(batch)

LOADERS = {"gleif": load_gleif, "wikidata": load_wikidata, "sec": load_sec, "uk": load_uk}
