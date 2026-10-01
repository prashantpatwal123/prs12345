# Notes for Claude Code
This repo is a jobs MCP server (`jobs_mcp/`) and a dataset pipeline (`pipeline/`). See PIPELINE.md.
- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -e .`
- Run steps one at a time and check `jobs-pipeline stats` between them; all steps are resumable.
- Long steps (`universe --sources gleif`, `scan-domains`, `sync`): run in the background with
  `caffeinate -i nohup jobs-pipeline <step> > logs/<step>.log 2>&1 &` and tail the log.
- If Common Crawl's index server returns 503, pass `--crawl-ids CC-MAIN-2026-39,...` to `discover`.
- Never store users' passwords in this database; never automate CAPTCHAs.
