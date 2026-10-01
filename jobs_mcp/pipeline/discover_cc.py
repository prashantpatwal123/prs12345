"""Step 2a – reverse discovery: find every employer that uses a supported job board
by scanning the Common Crawl URL index (public parquet on data.commoncrawl.org).

The index is sorted by SURT key, so DuckDB reads only the row groups covering e.g.
'io,greenhouse,' – a full crawl scan for all boards takes minutes, not days."""
import gzip, json, re, sys, time, urllib.request
import duckdb
from .db import CACHE

BASE = "https://data.commoncrawl.org/"
# ats -> (surt prefix, regex extracting the board token from a URL)
TARGETS = {
    "greenhouse":      ("io,greenhouse,", r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)"),
    "lever":           ("co,lever,",      r"jobs\.(?:eu\.)?lever\.co/([A-Za-z0-9_.-]+)"),
    "ashby":           ("com,ashbyhq,",   r"jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]+)"),
    "workable":        ("com,workable,",  r"apply\.workable\.com/([A-Za-z0-9_-]+)"),
    "smartrecruiters": ("com,smartrecruiters,", r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9_-]+)"),
    "recruitee":       ("com,recruitee,", r"//([a-z0-9-]+)\.recruitee\.com"),
    "personio":        ("de,personio,",   r"//([a-z0-9-]+)\.jobs\.personio\.de"),
    "breezy":          ("hr,breezy,",     r"//([a-z0-9-]+)\.breezy\.hr"),
    "workday":         ("com,myworkdayjobs,", r"//([a-z0-9-]+\.wd\d+\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?[A-Za-z0-9_-]+)"),
}
BAD = {"embed", "api", "v1", "j", "jobs", "widget", "static", "assets", "www", "app", "help", "support",
       "careers", "robots.txt", "favicon.ico", "sitemap.xml", "login", "en-us", "en-gb", "wday", "job"}

KNOWN = ["CC-MAIN-2026-39", "CC-MAIN-2026-34", "CC-MAIN-2026-30", "CC-MAIN-2026-26", "CC-MAIN-2026-21", "CC-MAIN-2026-17"]

def list_crawls(n: int) -> list[str]:
    """Latest crawl ids. The index server is often overloaded, so retry, then fall back
    to crawls whose files we've already cached plus a known list."""
    for attempt in range(4):
        try:
            data = json.load(urllib.request.urlopen("https://index.commoncrawl.org/collinfo.json", timeout=30))
            return [d["id"] for d in data[:n]]
        except Exception:
            time.sleep(5 * (attempt + 1))
    cached = sorted((p.stem.removeprefix("ccstats-") for p in CACHE.glob("ccstats-*.json")), reverse=True)
    print("  crawl list unavailable; using cached/known crawl ids", file=sys.stderr)
    return list(dict.fromkeys(cached + KNOWN))[:n]

def _stats(con, crawl):
    cache = CACHE / f"ccstats-{crawl}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    paths = [l.decode().strip() for l in gzip.open(urllib.request.urlopen(f"{BASE}crawl-data/{crawl}/cc-index-table.paths.gz"))]
    files = [BASE + p for p in paths if "subset=warc/" in p]
    print(f"  {crawl}: reading {len(files)} parquet footers (once, then cached)…", file=sys.stderr)
    rows = con.execute(f"""SELECT file_name, min(stats_min_value), max(stats_max_value) FROM parquet_metadata({files!r})
                           WHERE path_in_schema='url_surtkey' GROUP BY 1""").fetchall()
    cache.write_text(json.dumps(rows))
    return rows

def discover(dbcon, crawls: int = 3, only: list[str] | None = None, crawl_ids: list[str] | None = None) -> dict:
    dd = duckdb.connect()
    dd.execute("INSTALL httpfs; LOAD httpfs; SET http_retries=8; SET http_timeout=120000;")
    found = {}
    for crawl in crawl_ids or list_crawls(crawls):
        stats = _stats(dd, crawl)
        for ats, (lo, pat) in TARGETS.items():
            if only and ats not in only:
                continue
            hi = lo[:-1] + chr(ord(lo[-1]) + 1)
            files = [f for f, mn, mx in stats if mx >= lo and mn < hi]
            if not files:
                continue
            try:
                toks = dd.execute(f"""SELECT DISTINCT regexp_extract(url, ?, 1) FROM read_parquet({files!r})
                                      WHERE url_surtkey >= ? AND url_surtkey < ? AND fetch_status = 200""",
                                  [pat, lo, hi]).fetchall()
            except Exception as e:
                print(f"  {crawl} {ats}: {e}", file=sys.stderr); continue
            new = 0
            now = time.time()
            for (t,) in toks:
                if not t or t.lower() in BAD or len(t) < 2:
                    continue
                if ats != "workday":
                    t = t.lower() if ats in ("recruitee", "personio", "breezy", "lever", "greenhouse") else t
                cur = dbcon.execute("INSERT OR IGNORE INTO boards(ats, token, discovered_via, first_found) VALUES (?,?,?,?)",
                                    (ats, t, f"commoncrawl:{crawl}", now))
                new += cur.rowcount
            dbcon.commit()
            found[f"{crawl}:{ats}"] = {"tokens": len(toks), "new": new}
            print(f"  {crawl} {ats:16} {len(toks):>7,} tokens  {new:>7,} new", file=sys.stderr)
    return found
