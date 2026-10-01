# Global companies + jobs pipeline

Builds the dataset the MCP server searches, in one SQLite file (`~/.jobs_mcp/jobs.db`).

| Step | Command | What it does | Mac runtime (estimate) |
|---|---|---|---|
| 1 Company universe | `jobs-pipeline universe --sources sec,wikidata,gleif` | Loads registries: GLEIF (~3.4M legal entities worldwide, active and lapsed), Wikidata companies with websites (all countries), US SEC filers. Add `uk` for Companies House (~5M, big download). | 30–90 min |
| 2a Employer discovery | `jobs-pipeline discover --crawls 3` | Scans the Common Crawl URL index for every company using a supported job board. One crawl found ~17,000 boards in 16 seconds in testing. | 10–20 min (first run reads index metadata) |
| 2b Careers-page scan | `jobs-pipeline scan-domains --limit 50000` | Opens the website of each universe company, finds its careers page and the board behind it. ~2 domains/sec; leave it overnight. | hours; resumable |
| 3 Validate | `jobs-pipeline validate` | Checks each board is live, counts jobs, gets the company name, registers it for search. ~91% of discovered boards were live in testing. | ~30 min per 20k boards |
| Link | `jobs-pipeline link` | Attaches boards to registry companies (HQ country, legal entity). | seconds |
| 4 Sync jobs | `jobs-pipeline sync` | Pulls every open job. Test: 150 companies, 6,481 jobs in 29 s. Re-run daily; vanished jobs become `not_seen`. | 1–3 h first run |
| Status | `jobs-pipeline stats` | Counts per step. | – |

`jobs-pipeline all` runs everything in order. Every step is resumable – stop it any time and re-run.

## Setup on a Mac
```bash
cd ~/Downloads/jobs_mcp           # unzipped folder
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
caffeinate -i jobs-pipeline all   # caffeinate keeps the Mac awake
```
Disk: plan for 10–20 GB once jobs from tens of thousands of companies are stored.

## Coverage, honestly
- Universe ≠ employers. Registries list millions of entities; most have no careers page.
  The jobs layer covers companies whose jobs are machine-readable.
- Supported boards: Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee,
  Personio, Breezy, Workday, plus any careers page with schema.org JobPosting markup.
- Not yet: Taleo, SuccessFactors, iCIMS, Oracle – common at banks, Indian and Gulf
  corporates. These are the next adapters.
- Lever blocks most crawling, so Lever companies are found mainly via step 2b.
- Workday feeds cap at 2,000 roles per company.

## Using it
- Claude Desktop / Claude Code: add `jobs-mcp` as an MCP server (see README).
- Remote (Claude custom connector, ChatGPT): `jobs-mcp --http --port 8000`, behind HTTPS + auth.
