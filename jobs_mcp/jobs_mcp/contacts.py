"""Find who to contact about a job.

Sources, in order of trust:
 1. Contact data the ATS publishes on the posting (Recruitee mailbox, SmartRecruiters posting owner).
 2. Names / emails written in the job description itself.
 3. Recruiting mailboxes published on the company's own careers/contact pages.
 4. Optional: Hunter.io (set HUNTER_API_KEY) – returns publicly-sourced HR/recruiting
    contacts with confidence scores and can locate the email of a named contact.
Emails are never pattern-guessed (first.last@...) – only published or provider-sourced ones."""
import json, os, re
from urllib.parse import urljoin, urlparse
import httpx
from .ats import client
from .text import extract_emails, extract_named_contacts, is_generic_mailbox

HUNTER = "https://api.hunter.io/v2"
RECRUIT_TITLES = re.compile(r"recruit|talent|people|hr\b|human resources|hiring|acquisition", re.I)

def domain_of(company: dict, job: dict | None = None) -> str | None:
    if company.get("domain"):
        return company["domain"].lower().removeprefix("www.")
    for u in [company.get("careers_url"), (job or {}).get("url")]:
        host = urlparse(u or "").netloc.lower().removeprefix("www.")
        if host and not any(x in host for x in ("greenhouse", "lever.co", "ashbyhq", "workable", "smartrecruiters", "recruitee")):
            return host
    return None

async def from_company_site(domain: str | None, careers_url: str | None) -> list[dict]:
    urls = [u for u in [careers_url] if u and domain and domain in u]
    if domain:
        urls += [f"https://{domain}/{p}" for p in ("careers", "jobs", "contact", "contact-us")]
    out = []
    async with client() as c:
        for u in dict.fromkeys(urls):
            try:
                r = await c.get(u)
                if r.status_code != 200: continue
                for e in extract_emails(r.text):
                    if domain and not e.endswith(domain.split(".", 1)[-1] if domain.count(".") > 1 else domain): continue
                    if is_generic_mailbox(e):
                        out.append({"name": None, "title": "Recruiting mailbox", "email": e, "source": f"company site: {u}", "confidence": 0.7})
            except httpx.HTTPError:
                continue
    return out

async def from_hunter(domain: str, names: list[str]) -> list[dict]:
    key = os.environ.get("HUNTER_API_KEY")
    if not key or not domain:
        return []
    out = []
    async with httpx.AsyncClient(timeout=30) as c:
        for n in names[:3]:
            first, *rest = n.split()
            r = await c.get(f"{HUNTER}/email-finder", params={"domain": domain, "first_name": first, "last_name": " ".join(rest), "api_key": key})
            d = (r.json() or {}).get("data") or {}
            if d.get("email"):
                out.append({"name": n, "title": d.get("position"), "email": d["email"], "source": "hunter.io email-finder",
                            "confidence": (d.get("score") or 0) / 100, "verified": (d.get("verification") or {}).get("status") == "valid"})
        r = await c.get(f"{HUNTER}/domain-search", params={"domain": domain, "department": "hr", "limit": 10, "api_key": key})
        for e in ((r.json() or {}).get("data") or {}).get("emails", []):
            name = " ".join(x for x in [e.get("first_name"), e.get("last_name")] if x) or None
            out.append({"name": name, "title": e.get("position"), "email": e.get("value"),
                        "source": "hunter.io domain-search (HR)", "confidence": (e.get("confidence") or 0) / 100,
                        "verified": (e.get("verification") or {}).get("status") == "valid",
                        "linkedin": e.get("linkedin")})
    return out

async def find(job: dict, company: dict, use_hunter: bool = True) -> dict:
    found = []
    raw = json.loads(job["raw_contact"]) if job.get("raw_contact") else None
    if raw:
        found.append({"name": raw.get("name"), "title": "Posting owner" if raw.get("name") else "Application mailbox",
                      "email": raw.get("email"), "source": raw["source"], "confidence": 0.9})
    desc = job.get("description") or ""
    for e in extract_emails(desc):
        found.append({"name": None, "title": None, "email": e, "source": "job description", "confidence": 0.85})
    names = extract_named_contacts(desc)
    if raw and raw.get("name"): names.insert(0, raw["name"])
    for n in names:
        if not any(f.get("name") == n for f in found):
            found.append({"name": n, "title": "Named in posting", "email": None, "source": "job description", "confidence": 0.6})
    dom = domain_of(company, job)
    found += await from_company_site(dom, company.get("careers_url"))
    if use_hunter:
        found += await from_hunter(dom, names)
    # dedupe by email/name, keep highest confidence; rank recruiters first
    best = {}
    for f in found:
        k = (f.get("email") or "", f.get("name") or "")
        if k not in best or f["confidence"] > best[k]["confidence"]:
            best[k] = f
    ranked = sorted(best.values(), key=lambda f: (not RECRUIT_TITLES.search(f.get("title") or ""), -f["confidence"]))
    return {"domain": dom, "contacts": ranked,
            "hunter_enabled": bool(os.environ.get("HUNTER_API_KEY")),
            "note": None if ranked else "No published contact found. Apply via apply_url, or set HUNTER_API_KEY for provider lookup."}
