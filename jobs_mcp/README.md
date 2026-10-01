# jobs-mcp

An MCP server that builds a searchable index of jobs pulled straight from company
career sections worldwide, finds who to contact for each role, and scores candidate fitment.

## How jobs are extracted

Most company careers pages are front-ends for an applicant-tracking system (ATS) that
publishes a free, public job-board API. The server detects which one a careers URL uses
and reads it directly – structured, complete and far more reliable than HTML scraping.

| ATS | Coverage notes |
|---|---|
| Greenhouse, Lever, Ashby, Workable, Recruitee, Personio | Full descriptions in one call |
| Breezy | List only; descriptions on the job page |
| SmartRecruiters, Workday | List first; descriptions on demand or with `fetch_descriptions=true` |
| Anything else | schema.org `JobPosting` JSON-LD on the careers page and linked job pages |

Not yet covered: Taleo, SuccessFactors, iCIMS, Oracle Recruiting (next adapters to add).

## Tools

| Tool | Purpose |
|---|---|
| `jobs_add_company` | Register a careers URL, auto-detect ATS, sync |
| `jobs_import_companies` | Bulk import from `companies.yaml` |
| `jobs_list_companies` | Tracked companies, open-job counts, sync errors |
| `jobs_sync` | Refresh jobs; marks vanished jobs `not_seen` |
| `jobs_search` | Filters: keywords (AND), role/profile (OR on title), exclude, location, remote, company, department, posted_within_days; paginated |
| `jobs_get` | Full job incl. description and apply URL |
| `jobs_find_contacts` | Contact person / mailbox with source + confidence |
| `jobs_save_candidate` | Store a candidate profile |
| `jobs_check_fitment` | 0–100 score, breakdown, matched/missing skills, blockers |
| `jobs_match` | Search + rank all results for a candidate |

## Contacts – what it does and doesn't do
Order of trust: contact data the ATS publishes on the posting → names/emails in the job
description → recruiting mailboxes on the company's own site → Hunter.io (optional,
`HUNTER_API_KEY`) for publicly-sourced HR contacts and emails of people named in the posting.
Every result carries `source` and `confidence`. Emails are **never pattern-guessed**.
If you contact individuals, you're processing personal data: keep outreach relevant to
the role, honour opt-outs, and check GDPR/PDPA/DPDP rules for the countries involved.

## Fitment
Skills 40 · Experience 25 · Role/seniority 15 · Location 10 · Education 10.
Blockers (cap score at 45): large experience gap, location mismatch without relocation,
work-authorisation / no-sponsorship clauses. It's deterministic and explainable – ask
Claude to read the full JD (`jobs_get`) for a judgement call on borderline cases.

## Liveness (phase 2 – foundation in place)
Each sync records `first_seen` / `last_seen` and flips jobs missing from the board to
`not_seen`. Searches exclude those by default. Phase 2 will add per-job URL checks
(HTTP status, "no longer accepting applications" text, JSON-LD `validThrough`) and a
scheduled sync.

## Building the global dataset
See `PIPELINE.md` – registries → career-page discovery → validation → job sync.

## Remote connector (Claude custom connector / ChatGPT)
`jobs-mcp --http --port 8000` serves Streamable HTTP at `/mcp`. Host it behind HTTPS with auth before sharing.

## Install

```bash
pip install -e .            # Python 3.10+
jobs-mcp                    # runs over stdio
```

Claude Desktop – `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "jobs": {
      "command": "jobs-mcp",
      "env": { "JOBS_MCP_DB": "/Users/you/.jobs_mcp/jobs.db", "HUNTER_API_KEY": "" }
    }
  }
}
```
Then ask Claude: *"Import companies from /path/companies.yaml and sync them"*,
*"Find FP&A or BI manager roles in Singapore or Dubai posted in the last 14 days"*,
*"Rank them for my profile and find the recruiter for the top 3."*
