"""Global companies + jobs pipeline.

  python -m pipeline universe --sources sec,wikidata,gleif,uk   # step 1: company universe
  python -m pipeline discover --crawls 3                        # step 2a: employers via Common Crawl
  python -m pipeline scan-domains --limit 20000                 # step 2b: careers pages of universe companies
  python -m pipeline validate                                   # step 3: live boards -> MCP companies
  python -m pipeline link                                       # attach boards to registry companies
  python -m pipeline sync --stale-hours 24                      # step 4: pull jobs
  python -m pipeline all                                        # everything, in order
  python -m pipeline stats
Every step is resumable: re-running skips work already done.
"""
import argparse, asyncio, json, logging, sys, time
logging.getLogger("httpx").setLevel(logging.WARNING)
from . import db, sources, discover_cc, discover_domains, validate

def log_run(con, step, t0, detail):
    con.execute("INSERT INTO runs VALUES (?,?,?,?)", (step, t0, time.time(), json.dumps(detail, default=str)))
    con.commit()
    print(f"[{step}] {detail}  ({time.time()-t0:,.0f}s)")

def cmd_universe(con, a):
    for s in a.sources.split(","):
        t0 = time.time(); print(f"[universe] loading {s}…", file=sys.stderr)
        kw = {"countries": a.countries.split(",")} if s == "wikidata" and a.countries else {}
        log_run(con, f"universe:{s}", t0, {"rows": sources.LOADERS[s](con, **kw)})

def cmd_discover(con, a):
    t0 = time.time()
    log_run(con, "discover", t0, discover_cc.discover(con, a.crawls, a.only.split(",") if a.only else None, a.crawl_ids.split(",") if getattr(a, "crawl_ids", None) else None))

def cmd_scan(con, a):
    t0 = time.time()
    log_run(con, "scan-domains", t0, asyncio.run(discover_domains.run(con, a.limit, a.concurrency)))

def cmd_validate(con, a):
    t0 = time.time()
    log_run(con, "validate", t0, asyncio.run(validate.run(con, concurrency=a.concurrency, limit=a.limit)))

def cmd_link(con, a):
    t0 = time.time(); log_run(con, "link", t0, {"linked": validate.link(con)})

def cmd_sync(con, a):
    from jobs_mcp import server
    cutoff = time.time() - a.stale_hours * 3600
    ids = [r[0] for r in con.execute("""SELECT id FROM companies WHERE IFNULL(last_synced,0) < ?
                                        ORDER BY last_synced IS NOT NULL, id LIMIT ?""", (cutoff, a.limit))]
    t0 = time.time(); print(f"[sync] {len(ids):,} companies", file=sys.stderr)
    async def go():
        sem = asyncio.Semaphore(a.concurrency); done = {"ok": 0, "err": 0, "jobs": 0}
        async def one(cid):
            async with sem:
                r = await server._sync_one(con, cid, a.max_jobs, a.descriptions)
                done["err" if "error" in r else "ok"] += 1; done["jobs"] += r.get("fetched", 0)
                n = done["ok"] + done["err"]
                if n % 100 == 0: print(f"\r  {n:,}/{len(ids):,} {done}", end="", file=sys.stderr)
        await asyncio.gather(*(one(i) for i in ids))
        print(file=sys.stderr); return done
    log_run(con, "sync", t0, asyncio.run(go()))

def cmd_stats(con, a):
    q = lambda s: con.execute(s).fetchall()
    out = {
        "universe_by_source": dict(q("SELECT source, COUNT(*) FROM universe GROUP BY 1")),
        "universe_with_domain": q("SELECT COUNT(DISTINCT domain) FROM universe WHERE domain IS NOT NULL")[0][0],
        "domains_scanned": dict(q("SELECT result, COUNT(*) FROM domain_scan GROUP BY 1")),
        "boards_by_status": dict(q("SELECT status, COUNT(*) FROM boards GROUP BY 1")),
        "active_boards_by_ats": dict(q("SELECT ats, COUNT(*) FROM boards WHERE status='active' GROUP BY 1 ORDER BY 2 DESC")),
        "boards_linked_to_registry": q("SELECT COUNT(*) FROM boards WHERE universe_id IS NOT NULL")[0][0],
        "companies_in_mcp": q("SELECT COUNT(*) FROM companies")[0][0],
        "open_jobs": q("SELECT COUNT(*) FROM jobs WHERE status='open'")[0][0],
        "jobs_no_longer_listed": q("SELECT COUNT(*) FROM jobs WHERE status='not_seen'")[0][0],
    }
    print(json.dumps(out, indent=2))

def main():
    p = argparse.ArgumentParser(prog="pipeline", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    u = sp.add_parser("universe"); u.add_argument("--sources", default="sec,wikidata,gleif"); u.add_argument("--countries", help="wikidata only, e.g. SG,IN,AE")
    d = sp.add_parser("discover"); d.add_argument("--crawls", type=int, default=3); d.add_argument("--only"); d.add_argument("--crawl-ids", help="e.g. CC-MAIN-2026-39,CC-MAIN-2026-34")
    s = sp.add_parser("scan-domains"); s.add_argument("--limit", type=int, default=20000); s.add_argument("--concurrency", type=int, default=40)
    v = sp.add_parser("validate"); v.add_argument("--limit", type=int, default=200000); v.add_argument("--concurrency", type=int, default=25)
    sp.add_parser("link")
    y = sp.add_parser("sync"); y.add_argument("--stale-hours", type=float, default=24); y.add_argument("--limit", type=int, default=1000000)
    y.add_argument("--concurrency", type=int, default=12); y.add_argument("--max-jobs", type=int, default=3000)
    y.add_argument("--descriptions", action="store_true", help="also fetch Workday/SmartRecruiters descriptions (slow)")
    al = sp.add_parser("all"); al.add_argument("--sources", default="sec,wikidata,gleif"); al.add_argument("--crawls", type=int, default=3)
    al.add_argument("--scan-limit", type=int, default=50000)
    sp.add_parser("stats")
    a = p.parse_args()
    con = db.connect()
    if a.cmd == "all":
        ns = argparse.Namespace
        cmd_universe(con, ns(sources=a.sources, countries=None))
        cmd_discover(con, ns(crawls=a.crawls, only=None))
        cmd_scan(con, ns(limit=a.scan_limit, concurrency=40))
        cmd_validate(con, ns(limit=1000000, concurrency=25))
        cmd_link(con, ns())
        cmd_sync(con, ns(stale_hours=24, limit=1000000, concurrency=12, max_jobs=3000, descriptions=False))
        cmd_stats(con, ns())
    else:
        {"universe": cmd_universe, "discover": cmd_discover, "scan-domains": cmd_scan, "validate": cmd_validate,
         "link": cmd_link, "sync": cmd_sync, "stats": cmd_stats}[a.cmd](con, a)

if __name__ == "__main__":
    main()
