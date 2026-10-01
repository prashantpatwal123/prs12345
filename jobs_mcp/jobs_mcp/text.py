"""Text helpers: HTML to plain text, email extraction."""
import html, re
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
GENERIC_PREFIXES = ("careers", "jobs", "recruit", "talent", "hr", "hiring", "people", "apply", "resume", "cv")
IGNORE_EMAIL = ("noreply", "no-reply", "example.com", "sentry", ".png", ".jpg", "privacy", "accommodation", "accessib",
                "security", "dpo@", "legal@", "support", "fraud", "abuse", "compliance", "ethics")

def html_to_text(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    return re.sub(r"\n{3,}", "\n\n", BeautifulSoup(s, "html.parser").get_text("\n")).strip()

def extract_emails(text: str) -> list[str]:
    out = []
    for e in EMAIL_RE.findall(text or ""):
        e = e.strip(".").lower()
        if any(x in e for x in IGNORE_EMAIL) or e in out:
            continue
        out.append(e)
    return out

def is_generic_mailbox(email: str) -> bool:
    return email.split("@")[0].startswith(GENERIC_PREFIXES)

NAME_LINE_RE = re.compile(
    r"(?:hiring manager|recruiter|contact person|reach out to|contact|reporting to)\s*[:\-–]\s*"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+){1,2})")

def extract_named_contacts(text: str) -> list[str]:
    return list(dict.fromkeys(NAME_LINE_RE.findall(text or "")))
