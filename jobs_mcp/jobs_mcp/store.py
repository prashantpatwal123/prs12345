"""SQLite storage for companies, jobs and contacts."""
import json, os, sqlite3, time
from pathlib import Path

DB_PATH = Path(os.environ.get("JOBS_MCP_DB", Path.home() / ".jobs_mcp" / "jobs.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, ats TEXT NOT NULL, token TEXT,
  careers_url TEXT, domain TEXT, country TEXT, industry TEXT,
  last_synced REAL, last_error TEXT, UNIQUE(ats, token, careers_url));
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies(id),
  title TEXT, department TEXT, location TEXT, country TEXT, remote INTEGER,
  employment_type TEXT, url TEXT, apply_url TEXT, description TEXT,
  salary TEXT, posted_at TEXT, first_seen REAL, last_seen REAL,
  status TEXT DEFAULT 'open', raw_contact TEXT);
CREATE INDEX IF NOT EXISTS ix_jobs_company ON jobs(company_id);
CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs(status);
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, job_id TEXT,
  name TEXT, title TEXT, email TEXT, source TEXT, confidence REAL,
  verified INTEGER DEFAULT 0, found_at REAL,
  UNIQUE(company_id, job_id, email, name));
"""

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con

def upsert_company(con, **c) -> int:
    row = con.execute("SELECT id FROM companies WHERE ats=? AND IFNULL(token,'')=IFNULL(?,'') AND IFNULL(careers_url,'')=IFNULL(?,'')",
                      (c["ats"], c.get("token"), c.get("careers_url"))).fetchone()
    if row:
        con.execute("UPDATE companies SET name=?, domain=COALESCE(?,domain), country=COALESCE(?,country), industry=COALESCE(?,industry) WHERE id=?",
                    (c["name"], c.get("domain"), c.get("country"), c.get("industry"), row["id"]))
        return row["id"]
    cur = con.execute("INSERT INTO companies(name, ats, token, careers_url, domain, country, industry) VALUES (?,?,?,?,?,?,?)",
                      (c["name"], c["ats"], c.get("token"), c.get("careers_url"), c.get("domain"), c.get("country"), c.get("industry")))
    return cur.lastrowid

def save_jobs(con, company_id: int, jobs: list[dict], complete: bool = True) -> dict:
    """Upsert jobs; anything for this company not seen in this sync becomes 'not_seen'.
    This is the foundation for the later liveness check."""
    now = time.time()
    new = 0
    for j in jobs:
        exists = con.execute("SELECT 1 FROM jobs WHERE id=?", (j["id"],)).fetchone()
        if not exists:
            new += 1
        con.execute("""INSERT INTO jobs(id, company_id, title, department, location, country, remote, employment_type,
                         url, apply_url, description, salary, posted_at, first_seen, last_seen, status, raw_contact)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open',?)
                       ON CONFLICT(id) DO UPDATE SET title=excluded.title, department=excluded.department,
                         location=excluded.location, country=excluded.country, remote=excluded.remote,
                         employment_type=excluded.employment_type, url=excluded.url, apply_url=excluded.apply_url,
                         description=excluded.description, salary=excluded.salary, posted_at=excluded.posted_at,
                         last_seen=excluded.last_seen, status='open', raw_contact=excluded.raw_contact""",
                    (j["id"], company_id, j.get("title"), j.get("department"), j.get("location"), j.get("country"),
                     None if j.get("remote") is None else int(bool(j["remote"])), j.get("employment_type"),
                     j.get("url"), j.get("apply_url"), j.get("description"), j.get("salary"), j.get("posted_at"),
                     now, now, json.dumps(j.get("contact")) if j.get("contact") else None))
    ids = [j["id"] for j in jobs]
    q = "UPDATE jobs SET status='not_seen' WHERE company_id=? AND status='open'"
    if ids:
        q += f" AND id NOT IN ({','.join('?' * len(ids))})"
    # only mark missing jobs when we fetched the full board (a capped fetch would give false 'gone')
    gone = con.execute(q, (company_id, *ids)).rowcount if complete else 0
    con.execute("UPDATE companies SET last_synced=?, last_error=NULL WHERE id=?", (now, company_id))
    con.commit()
    return {"fetched": len(jobs), "new": new, "no_longer_listed": gone}
