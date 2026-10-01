"""Pipeline tables, stored in the same SQLite file the MCP server reads."""
import os, re, unicodedata
from pathlib import Path
from jobs_mcp import store

CACHE = Path(os.environ.get("JOBS_MCP_CACHE", Path.home() / ".jobs_mcp" / "cache"))
CACHE.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS universe (
  id INTEGER PRIMARY KEY, source TEXT NOT NULL, source_id TEXT NOT NULL, name TEXT NOT NULL,
  norm_name TEXT, country TEXT, domain TEXT, status TEXT, category TEXT, extra TEXT,
  UNIQUE(source, source_id));
CREATE INDEX IF NOT EXISTS ix_u_norm ON universe(norm_name);
CREATE INDEX IF NOT EXISTS ix_u_domain ON universe(domain);
CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY, ats TEXT NOT NULL, token TEXT NOT NULL, discovered_via TEXT,
  first_found REAL, last_checked REAL, status TEXT DEFAULT 'new', job_count INTEGER,
  board_name TEXT, universe_id INTEGER, company_id INTEGER, error TEXT,
  UNIQUE(ats, token));
CREATE INDEX IF NOT EXISTS ix_b_status ON boards(status);
CREATE TABLE IF NOT EXISTS domain_scan (
  domain TEXT PRIMARY KEY, checked_at REAL, careers_url TEXT, ats TEXT, token TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS runs (step TEXT, started REAL, finished REAL, detail TEXT);
"""

def connect():
    con = store.connect()
    con.executescript(SCHEMA)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con

SUFFIXES = r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|llc|llp|lp|plc|gmbh|ag|sa|sas|sarl|bv|nv|spa|srl|ab|as|asa|oy|kk|pte|pvt|private|pty|holdings?|group|the)\b"

def norm_name(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[&+]", " and ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(SUFFIXES, " ", s)
    return re.sub(r"\s+", " ", s).strip()

def norm_domain(url: str | None) -> str | None:
    if not url:
        return None
    d = re.sub(r"^[a-z]+://", "", url.strip().lower()).split("/")[0].split(":")[0]
    d = d.removeprefix("www.")
    return d if "." in d else None
