"""Rule-based fitment check between a candidate profile and a job.

Deterministic and explainable: returns a 0-100 score, per-dimension breakdown,
matched/missing skills and hard blockers. The calling LLM can layer judgement
on top using the full job description (jobs_get)."""
import re

SKILL_VOCAB = [
    # data / BI / finance
    "sql", "python", "excel", "vba", "power bi", "tableau", "looker", "qlik", "google sheets", "apps script",
    "dax", "power query", "snowflake", "bigquery", "databricks", "dbt", "airflow", "spark", "etl", "data modeling",
    "data warehouse", "statistics", "machine learning", "forecasting", "a/b testing", "financial modeling",
    "financial modelling", "fp&a", "budgeting", "variance analysis", "p&l", "ebitda", "consolidation", "ifrs",
    "gaap", "sap", "oracle", "netsuite", "tm1", "anaplan", "hyperion", "valuation", "m&a", "due diligence",
    "business intelligence", "kpi", "dashboards", "stakeholder management",
    # engineering
    "java", "javascript", "typescript", "react", "node.js", "golang", "rust", "c++", "c#", ".net", "kotlin",
    "swift", "aws", "azure", "gcp", "kubernetes", "docker", "terraform", "ci/cd", "linux", "graphql", "rest api",
    "microservices", "postgresql", "mysql", "mongodb", "redis", "kafka", "llm", "nlp", "pytorch", "tensorflow",
    # product / commercial / ops
    "product management", "roadmap", "agile", "scrum", "jira", "salesforce", "hubspot", "crm", "seo", "sem",
    "google analytics", "digital marketing", "content marketing", "b2b", "b2c", "saas", "sales", "account management",
    "business development", "negotiation", "project management", "pmp", "six sigma", "supply chain",
    "procurement", "customer success", "recruiting", "hris", "payroll", "admissions", "edtech",
    "curriculum", "teaching", "education management",
]
SENIORITY = [  # (level, patterns)
    (0, r"\bintern(ship)?\b|\btrainee\b|\bgraduate\b"), (1, r"\bjunior\b|\bjr\.?\b|\bentry\b|\bassociate\b"),
    (3, r"\bsenior\b|\bsr\.?\b"), (4, r"\blead\b|\bstaff\b|\bprincipal\b"),
    (4, r"\bmanager\b"), (5, r"\bsenior manager\b|\bhead of\b|\bdirector\b"),
    (6, r"\bvp\b|\bvice president\b|\bchief\b|\bc[etfo]o\b"),
]
DEGREES = [("phd", r"\bph\.?d\b|\bdoctorate\b"), ("masters", r"\bmaster'?s\b|\bm\.?s\.?c?\b|\bmba\b"),
           ("bachelors", r"\bbachelor'?s\b|\bb\.?(sc|a|tech|e|com)\b|\bundergraduate degree\b"),
           ("ca/cpa/cfa", r"\bchartered accountant\b|\bcpa\b|\bcfa\b|\bacca\b|\bcima\b")]
DEGREE_RANK = {"bachelors": 1, "masters": 2, "phd": 3}
AUTH_PATTERNS = [r"(?:must|need to) (?:be|have) (?:legally )?(?:authori[sz]ed|eligible|the right) to work in ([A-Z][A-Za-z .]+)",
                 r"right to work in (?:the )?([A-Z][A-Za-z .]+)", r"(no|not able to|unable to|cannot|do not) (?:offer |provide )?(?:visa )?sponsor"]

def _has(term, text):
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])", text, re.I) is not None

def seniority_of(title: str) -> int:
    lvl = 2
    for level, pat in SENIORITY:
        if re.search(pat, title or "", re.I):
            lvl = max(lvl, level) if level > 1 else level
    return lvl

def required_years(text: str) -> float | None:
    yrs = []
    for m in re.finditer(r"(\d{1,2})\s*(?:\+|plus)?\s*(?:[-–to]+\s*\d{1,2}\s*)?\+?\s*years?", text, re.I):
        window = text[m.start(): m.end() + 80].lower()
        if "experience" in window or "exp" in window:
            yrs.append(int(m.group(1)))
    yrs = [y for y in yrs if 0 < y <= 25]
    return float(min(yrs)) if yrs else None

def check(job: dict, cand: dict) -> dict:
    title = job.get("title") or ""
    text = f"{title}\n{job.get('description') or ''}"
    blockers, notes = [], []

    # skills (40)
    cskills = [s.strip() for s in cand.get("skills", []) if s.strip()]
    matched = [s for s in cskills if _has(s, text)]
    jd_skills = [s for s in SKILL_VOCAB if _has(s, text)]
    missing = [s for s in jd_skills if not any(s.lower() == c.lower() for c in cskills)]
    denom = max(len(set(s.lower() for s in matched) | set(missing)), 1)
    ratio = len(matched) / denom if (matched or missing) else 0.5
    evidence = min(denom / 5, 1.0)  # little skill evidence in the JD -> pull towards neutral
    skill_score = 40 * (ratio * evidence + 0.5 * (1 - evidence))

    # experience (25)
    need = required_years(text)
    have = cand.get("years_experience")
    if need is None or have is None:
        exp_score = 17
        notes.append("Years of experience not stated in posting" if need is None else "Candidate years not provided")
    elif have >= need:
        exp_score = 25 if have <= need + 8 else 20
        if have > need + 8: notes.append(f"Possibly overqualified: {have} yrs vs {need}+ asked")
    else:
        gap = need - have
        exp_score = max(0, 25 - gap * 7)
        if gap >= 3: blockers.append(f"Experience gap: posting asks {need:g}+ yrs, candidate has {have:g}")

    # role / seniority (15)
    targets = cand.get("target_roles") or ([cand["current_title"]] if cand.get("current_title") else [])
    role_hit = any(all(_has(w, title) for w in t.lower().split() if len(w) > 2) for t in targets)
    jl = seniority_of(title)
    cl = seniority_of(cand.get("current_title", "")) if cand.get("current_title") else None
    role_score = 8 if role_hit else 3
    if cl is not None:
        diff = jl - cl
        role_score += 7 if diff in (0, 1) else 4 if diff == -1 else 0
        if diff >= 2: notes.append("Role is 2+ levels above current title")
        if diff <= -2: notes.append("Role is 2+ levels below current title")
    else:
        role_score += 4

    # location (10)
    jloc = f"{job.get('location') or ''} {job.get('country') or ''}".lower()
    prefs = [p.lower() for p in cand.get("locations", [])]
    loc_ok = any(p in jloc for p in prefs)
    if job.get("remote") and cand.get("open_to_remote", True):
        loc_score = 10
    elif loc_ok:
        loc_score = 10
    elif cand.get("open_to_relocate"):
        loc_score = 6; notes.append("Requires relocation")
    else:
        loc_score = 2 if prefs else 6
        if prefs:
            blockers.append(f"Location mismatch: job in '{job.get('location')}', candidate prefers {', '.join(cand.get('locations', []))} and is not open to relocate")
    auth = cand.get("work_authorization") or []
    if auth and not job.get("remote") and jloc.strip() and not any(a.lower() in jloc for a in auth) and not loc_ok:
        notes.append("Job location is outside candidate's work-authorised countries – likely needs sponsorship")

    # education (10)
    req = [d for d, pat in DEGREES if re.search(pat, text, re.I)]
    cedu = (cand.get("education") or "").lower()
    cands = {d for d, pat in DEGREES if re.search(pat, cedu, re.I)}
    if not req:
        edu_score = 10
    else:
        need_rank = min((DEGREE_RANK[d] for d in req if d in DEGREE_RANK), default=0)
        have_rank = max((DEGREE_RANK[d] for d in cands if d in DEGREE_RANK), default=0)
        edu_score = 10 if have_rank >= need_rank else 5
        if "ca/cpa/cfa" in req and "ca/cpa/cfa" not in cands:
            notes.append("Posting mentions a professional qualification (CA/CPA/CFA/ACCA/CIMA)")

    # work authorisation (blocker only, no points)
    for pat in AUTH_PATTERNS:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        if m.lastindex and m.group(1) and not m.group(1).lower().startswith(("no", "not", "unable", "cannot", "do")):
            place = m.group(1).strip().split(".")[0][:40]
            if auth and not any(a.lower() in place.lower() for a in auth):
                blockers.append(f"Work authorisation required for {place}")
        else:
            if auth and not any(a.lower() in jloc for a in auth):
                blockers.append("Posting says no visa sponsorship; candidate may need it")

    score = round(skill_score + exp_score + role_score + loc_score + edu_score)
    if blockers: score = min(score, 45)
    verdict = "strong fit" if score >= 75 else "good fit" if score >= 60 else "stretch" if score >= 45 else "weak fit"
    return {"score": score, "verdict": verdict, "eligible": not blockers,
            "breakdown": {"skills": round(skill_score), "experience": round(exp_score), "role_seniority": round(role_score),
                          "location": loc_score, "education": edu_score},
            "matched_skills": matched, "missing_skills": missing[:15], "required_years": need,
            "blockers": blockers, "notes": notes}
