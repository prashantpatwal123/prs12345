"""jobs_mcp – MCP server that indexes jobs from company career sections worldwide."""
import asyncio, json, time
from typing import Optional, List
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
try:  # mcp SDK 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp SDK 1.x
    from mcp.server.fastmcp import FastMCP as _Server
from mcp.types import ToolAnnotations
import yaml
from . import ats, contacts, fitment, store

mcp = _Server("jobs_mcp", instructions="Index and search jobs from company career sections worldwide; find contacts and check candidate fitment. Typical flow: jobs_add_company / jobs_import_companies -> jobs_sync -> jobs_search or jobs_match -> jobs_get -> jobs_check_fitment -> jobs_find_contacts.")
RO = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}

def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)

def _company(con, cid):
    r = con.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    return dict(r) if r else None

def _job(con, job_id):
    r = con.execute("SELECT j.*, c.name AS company FROM jobs j JOIN companies c ON c.id=j.company_id WHERE j.id=?", (job_id,)).fetchone()
    return dict(r) if r else None

async def _ensure_detail(con, job):
    if not job.get("description"):
        d = await ats.fetch_detail(job["id"], job.get("url"))
        if d:
            con.execute("UPDATE jobs SET description=?, apply_url=COALESCE(?,apply_url), url=COALESCE(?,url), raw_contact=COALESCE(?,raw_contact) WHERE id=?",
                        (d.get("description"), d.get("apply_url"), d.get("url"), json.dumps(d["contact"]) if d.get("contact") else None, job["id"]))
            con.commit()
            job = _job(con, job["id"])
    return job

# ------------------------------------------------------------------ companies
class AddCompany(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    careers_url: str = Field(..., description="Company careers page or job-board URL, e.g. 'https://www.stripe.com/jobs' or 'https://jobs.lever.co/palantir'")
    name: Optional[str] = Field(None, description="Company name (defaults to the board token or domain)")
    country: Optional[str] = Field(None, description="HQ country, e.g. 'Singapore'")
    industry: Optional[str] = Field(None, description="e.g. 'Education', 'Fintech'")
    domain: Optional[str] = Field(None, description="Company email domain, e.g. 'stripe.com' (improves contact finding)")
    sync_now: bool = Field(True, description="Fetch jobs immediately")

async def _add(con, p: dict) -> dict:
    det = await ats.detect(p["careers_url"])
    name = p.get("name") or det["token"] or ats.urlparse(p["careers_url"]).netloc
    cid = store.upsert_company(con, name=name, ats=det["ats"], token=det["token"],
                               careers_url=p["careers_url"], domain=p.get("domain"),
                               country=p.get("country"), industry=p.get("industry"))
    con.commit()
    res = {"company_id": cid, "name": name, **det}
    if p.get("sync_now", True):
        res["sync"] = await _sync_one(con, cid)
    return res

@mcp.tool(name="jobs_add_company", annotations=ToolAnnotations(**{"title": "Add company careers page", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}))
async def jobs_add_company(params: AddCompany) -> str:
    """Register a company by its careers URL. Auto-detects the job board behind it
    (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee) or falls back to
    schema.org JobPosting scraping, then optionally syncs its jobs. Returns company_id and sync counts."""
    con = store.connect()
    try:
        return _j(await _add(con, params.model_dump()))
    except Exception as e:
        return f"Error adding company: {e}. Check the URL opens in a browser; if it is a custom page, pass the underlying job-board URL instead."

class ImportCompanies(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(..., description="Path to a YAML or JSON file: list of {careers_url, name?, country?, industry?, domain?}")
    sync_now: bool = Field(False, description="Sync every company after import (slower)")

@mcp.tool(name="jobs_import_companies", annotations=ToolAnnotations(**{"title": "Bulk import companies", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}))
async def jobs_import_companies(params: ImportCompanies) -> str:
    """Bulk-register companies from a YAML/JSON file. Returns per-company detection results and failures."""
    rows = yaml.safe_load(Path(params.path).expanduser().read_text())
    con = store.connect()
    ok, failed = [], []
    sem = asyncio.Semaphore(6)
    async def one(r):
        async with sem:
            try:
                ok.append(await _add(con, {**r, "sync_now": params.sync_now}))
            except Exception as e:
                failed.append({"careers_url": r.get("careers_url"), "error": str(e)})
    await asyncio.gather(*(one(r) for r in rows))
    return _j({"imported": len(ok), "failed": failed, "companies": [{k: c[k] for k in ("company_id", "name", "ats")} for c in ok]})

@mcp.tool(name="jobs_list_companies", annotations=ToolAnnotations(**{**RO, "title": "List tracked companies"}))
async def jobs_list_companies() -> str:
    """List tracked companies with ATS, open-job count, last sync time and last error."""
    con = store.connect()
    rows = con.execute("""SELECT c.id, c.name, c.ats, c.country, c.industry, c.careers_url,
        datetime(c.last_synced,'unixepoch') AS last_synced, c.last_error,
        SUM(j.status='open') AS open_jobs FROM companies c LEFT JOIN jobs j ON j.company_id=c.id
        GROUP BY c.id ORDER BY c.name""").fetchall()
    return _j([dict(r) for r in rows])

# ------------------------------------------------------------------ sync
async def _fill_descriptions(con, cid, cap=400):
    rows = con.execute("SELECT id, url FROM jobs WHERE company_id=? AND status='open' AND IFNULL(description,'')='' LIMIT ?", (cid, cap)).fetchall()
    sem = asyncio.Semaphore(8)
    async def one(r):
        async with sem:
            try:
                d = await ats.fetch_detail(r["id"], r["url"])
                if d.get("description"):
                    con.execute("UPDATE jobs SET description=?, raw_contact=COALESCE(?,raw_contact) WHERE id=?",
                                (d["description"], json.dumps(d["contact"]) if d.get("contact") else None, r["id"]))
                    return 1
            except Exception:
                pass
            return 0
    n = sum(await asyncio.gather(*(one(r) for r in rows)))
    con.commit()
    return n

async def _sync_one(con, cid, limit=3000, descriptions=False):
    comp = _company(con, cid)
    try:
        jobs = await ats.fetch_company_jobs(comp, limit)
        res = store.save_jobs(con, cid, jobs, complete=len(jobs) < limit)
        if len(jobs) >= limit: res["warning"] = f"Hit max_jobs_per_company={limit}; raise it to index the full board"
        if descriptions and comp["ats"] in ("workday", "smartrecruiters"):
            res["descriptions_fetched"] = await _fill_descriptions(con, cid)
        return res
    except Exception as e:
        con.execute("UPDATE companies SET last_error=? WHERE id=?", (str(e)[:300], cid)); con.commit()
        return {"error": str(e)[:300]}

class Sync(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_ids: Optional[List[int]] = Field(None, description="Companies to sync; omit for all")
    max_jobs_per_company: int = Field(3000, ge=1, le=20000)
    fetch_descriptions: bool = Field(False, description="Workday/SmartRecruiters list endpoints omit descriptions; set true to fetch them (up to 400 per company per run) so keyword search and jobs_match work on them")

@mcp.tool(name="jobs_sync", annotations=ToolAnnotations(**{"title": "Refresh jobs from career pages", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}))
async def jobs_sync(params: Sync) -> str:
    """Re-fetch jobs from companies' career sections. New jobs are added; jobs no longer
    listed are marked 'not_seen' (kept for history, excluded from search by default)."""
    con = store.connect()
    ids = params.company_ids or [r["id"] for r in con.execute("SELECT id FROM companies")]
    sem = asyncio.Semaphore(6)
    async def one(cid):
        async with sem:
            return cid, await _sync_one(con, cid, params.max_jobs_per_company, params.fetch_descriptions)
    res = dict(await asyncio.gather(*(one(i) for i in ids)))
    return _j({"synced": len(res), "results": res})

# ------------------------------------------------------------------ search
class Search(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    keywords: Optional[List[str]] = Field(None, description="All must appear in title or description, e.g. ['power bi','sql']")
    role: Optional[List[str]] = Field(None, description="Job role/profile – any may match the title, e.g. ['business intelligence','data analyst']")
    exclude: Optional[List[str]] = Field(None, description="Drop jobs whose title contains any of these, e.g. ['intern']")
    location: Optional[str] = Field(None, description="Substring of location or country, e.g. 'Singapore', 'London', 'IN'")
    remote: Optional[bool] = Field(None, description="True = remote only; False = non-remote only")
    company: Optional[str] = Field(None, description="Company name substring")
    department: Optional[str] = Field(None, description="Department substring, e.g. 'Finance'")
    posted_within_days: Optional[int] = Field(None, ge=1, le=365, description="Only jobs first seen/posted in the last N days")
    include_not_seen: bool = Field(False, description="Include jobs that disappeared from the careers page in the latest sync")
    limit: int = Field(25, ge=1, le=200)
    offset: int = Field(0, ge=0)

def _search_rows(con, p: Search, with_desc=False):
    where, args = ["1=1"], []
    if not p.include_not_seen: where.append("j.status='open'")
    for k in p.keywords or []:
        where.append("(j.title LIKE ? OR j.description LIKE ?)"); args += [f"%{k}%"] * 2
    if p.role:
        where.append("(" + " OR ".join(["j.title LIKE ?"] * len(p.role)) + ")"); args += [f"%{r}%" for r in p.role]
    for x in p.exclude or []:
        where.append("j.title NOT LIKE ?"); args.append(f"%{x}%")
    if p.location:
        where.append("(j.location LIKE ? OR j.country LIKE ? OR c.country LIKE ?)"); args += [f"%{p.location}%"] * 3
    if p.remote is not None:
        where.append("IFNULL(j.remote,0)=?"); args.append(int(p.remote))
    if p.company:
        where.append("c.name LIKE ?"); args.append(f"%{p.company}%")
    if p.department:
        where.append("j.department LIKE ?"); args.append(f"%{p.department}%")
    if p.posted_within_days:
        cutoff = time.time() - p.posted_within_days * 86400
        where.append("(j.first_seen>=? OR j.posted_at>=date('now', ?))"); args += [cutoff, f"-{p.posted_within_days} days"]
    cols = "j.id, c.name AS company, j.title, j.department, j.location, j.country, j.remote, j.employment_type, j.salary, j.posted_at, j.url, j.status"
    if with_desc: cols += ", j.description"
    sql = f"FROM jobs j JOIN companies c ON c.id=j.company_id WHERE {' AND '.join(where)}"
    total = con.execute(f"SELECT COUNT(*) {sql}", args).fetchone()[0]
    rows = con.execute(f"SELECT {cols} {sql} ORDER BY COALESCE(j.posted_at, datetime(j.first_seen,'unixepoch')) DESC LIMIT ? OFFSET ?",
                       [*args, p.limit, p.offset]).fetchall()
    return total, [dict(r) for r in rows]

@mcp.tool(name="jobs_search", annotations=ToolAnnotations(**{**RO, "title": "Search jobs"}))
async def jobs_search(params: Search) -> str:
    """Search indexed jobs by keywords, role/profile, location, remote, company, department and recency.
    Returns {total, count, has_more, next_offset, jobs[]} without descriptions (use jobs_get for full text)."""
    con = store.connect()
    total, rows = _search_rows(con, params)
    nxt = params.offset + len(rows)
    return _j({"total": total, "count": len(rows), "has_more": nxt < total, "next_offset": nxt if nxt < total else None, "jobs": rows})

class JobId(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str = Field(..., description="Job id from jobs_search, e.g. 'greenhouse:anthropic:4461450008'")

@mcp.tool(name="jobs_get", annotations=ToolAnnotations(**{**RO, "openWorldHint": True, "title": "Get full job"}))
async def jobs_get(params: JobId) -> str:
    """Full job record including description, apply URL, first/last seen and status."""
    con = store.connect()
    job = _job(con, params.job_id)
    if not job: return f"Job '{params.job_id}' not found. Use jobs_search to get valid ids."
    job = await _ensure_detail(con, job)
    job["first_seen"] = time.strftime("%Y-%m-%d", time.gmtime(job["first_seen"]))
    job["last_seen"] = time.strftime("%Y-%m-%d", time.gmtime(job["last_seen"]))
    job.pop("raw_contact", None)
    return _j(job)

# ------------------------------------------------------------------ contacts
class FindContacts(JobId):
    use_hunter: bool = Field(True, description="Also query Hunter.io if HUNTER_API_KEY is set")

@mcp.tool(name="jobs_find_contacts", annotations=ToolAnnotations(**{"title": "Find contact for a job", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}))
async def jobs_find_contacts(params: FindContacts) -> str:
    """Find the relevant person/mailbox to contact for a job: ATS-published contacts, names and
    emails in the posting, recruiting mailboxes on the company site, and optionally Hunter.io.
    Every result carries its source and a 0-1 confidence. Emails are never guessed."""
    con = store.connect()
    job = _job(con, params.job_id)
    if not job: return f"Job '{params.job_id}' not found."
    job = await _ensure_detail(con, job)
    comp = _company(con, job["company_id"])
    res = await contacts.find(job, comp, params.use_hunter)
    for c in res["contacts"]:
        con.execute("""INSERT OR REPLACE INTO contacts(company_id, job_id, name, title, email, source, confidence, verified, found_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""", (comp["id"], job["id"], c.get("name"), c.get("title"), c.get("email"),
                       c["source"], c["confidence"], int(bool(c.get("verified"))), time.time()))
    con.commit()
    return _j({"job_id": job["id"], "company": comp["name"], "apply_url": job.get("apply_url"), **res})

# ------------------------------------------------------------------ candidates & fitment
class Candidate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    skills: List[str] = Field(default_factory=list, description="e.g. ['SQL','Power BI','FP&A','financial modelling']")
    years_experience: Optional[float] = Field(None, ge=0, le=60)
    current_title: Optional[str] = Field(None, description="e.g. 'Business Intelligence Manager'")
    target_roles: List[str] = Field(default_factory=list, description="e.g. ['BI manager','FP&A manager']")
    locations: List[str] = Field(default_factory=list, description="Preferred cities/countries, e.g. ['Singapore','Dubai']")
    open_to_remote: bool = True
    open_to_relocate: bool = False
    work_authorization: List[str] = Field(default_factory=list, description="Countries the candidate can work in without sponsorship")
    education: Optional[str] = Field(None, description="e.g. 'MBA Finance, B.Com'")

class SaveCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., description="Label for this profile, e.g. 'prashant'")
    profile: Candidate

def _cand_table(con):
    con.execute("CREATE TABLE IF NOT EXISTS candidates(name TEXT PRIMARY KEY, profile TEXT)")

@mcp.tool(name="jobs_save_candidate", annotations=ToolAnnotations(**{"title": "Save candidate profile", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}))
async def jobs_save_candidate(params: SaveCandidate) -> str:
    """Save or overwrite a candidate profile used by jobs_check_fitment and jobs_match."""
    con = store.connect(); _cand_table(con)
    con.execute("INSERT OR REPLACE INTO candidates VALUES (?,?)", (params.name.lower(), params.profile.model_dump_json()))
    con.commit()
    return f"Saved candidate '{params.name.lower()}'."

def _load_cand(con, name, inline):
    if inline: return inline.model_dump()
    _cand_table(con)
    r = con.execute("SELECT profile FROM candidates WHERE name=?", ((name or "").lower(),)).fetchone()
    if not r: raise ValueError(f"No candidate '{name}'. Save one with jobs_save_candidate or pass 'profile'.")
    return json.loads(r["profile"])

class Fit(JobId):
    candidate: Optional[str] = Field(None, description="Saved candidate name")
    profile: Optional[Candidate] = Field(None, description="Inline profile (instead of a saved one)")

@mcp.tool(name="jobs_check_fitment", annotations=ToolAnnotations(**{**RO, "openWorldHint": True, "title": "Check candidate fitment"}))
async def jobs_check_fitment(params: Fit) -> str:
    """Score how well a candidate fits a job (0-100) with breakdown (skills 40, experience 25,
    role/seniority 15, location 10, education 10), matched/missing skills, eligibility blockers
    (experience gap, work authorisation / no sponsorship) and notes."""
    con = store.connect()
    try: cand = _load_cand(con, params.candidate, params.profile)
    except ValueError as e: return str(e)
    job = _job(con, params.job_id)
    if not job: return f"Job '{params.job_id}' not found."
    job = await _ensure_detail(con, job)
    return _j({"job_id": job["id"], "title": job["title"], "company": job["company"], **fitment.check(job, cand)})

class Match(Search):
    candidate: Optional[str] = Field(None, description="Saved candidate name")
    profile: Optional[Candidate] = None
    min_score: int = Field(50, ge=0, le=100)
    top_n: int = Field(15, ge=1, le=100)

@mcp.tool(name="jobs_match", annotations=ToolAnnotations(**{**RO, "title": "Rank jobs for a candidate"}))
async def jobs_match(params: Match) -> str:
    """Search with the same filters as jobs_search (up to 500 candidates), score every result
    for the candidate and return the top matches above min_score, best first."""
    con = store.connect()
    try: cand = _load_cand(con, params.candidate, params.profile)
    except ValueError as e: return str(e)
    s = Search(**params.model_dump(include=set(Search.model_fields)) | {"limit": 200, "offset": 0})
    total, rows = _search_rows(con, s, with_desc=True)
    for off in (200, 400):
        if off < total:
            rows += _search_rows(con, s.model_copy(update={"offset": off}), with_desc=True)[1]
    scored = []
    for r in rows:
        f = fitment.check(r, cand)
        if f["score"] >= params.min_score:
            scored.append({"job_id": r["id"], "company": r["company"], "title": r["title"], "location": r["location"],
                           "url": r["url"], "score": f["score"], "verdict": f["verdict"], "eligible": f["eligible"],
                           "missing_skills": f["missing_skills"][:5], "blockers": f["blockers"]})
    scored.sort(key=lambda x: (-x["eligible"], -x["score"]))
    return _j({"searched": len(rows), "matched": len(scored), "results": scored[:params.top_n]})

def main():
    """stdio by default (Claude Desktop / Claude Code). `jobs-mcp --http [--port 8000]` serves
    Streamable HTTP at /mcp for remote connectors (Claude custom connectors, ChatGPT).
    Put it behind HTTPS + auth before exposing it publicly."""
    import sys
    if "--http" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
        host = "0.0.0.0"
        if hasattr(mcp, "run_streamable_http_async") and "port" in str(__import__("inspect").signature(mcp.run_streamable_http_async)):
            mcp.run(transport="streamable-http", host=host, port=port)   # mcp SDK 2.x
        else:
            mcp.settings.host, mcp.settings.port = host, port              # mcp SDK 1.x
            mcp.run(transport="streamable-http")
    else:
        mcp.run()

if __name__ == "__main__":
    main()
