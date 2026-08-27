---
name: onboard
description: Onboard into this workflows codebase and provide a summary of its current state
---

Onboard into this workflows codebase and provide a summary of its current state.

## Steps

1. **Scan the project structure**
   - List all top-level files and directories
   - List all workflows in `workflows/`
   - List all plans in `.agent/plans/`

2. **Read key files**
   - `CLAUDE.md` — project conventions and rules
   - `CATALOG.md` — workflow index and status
   - `README.md` — project overview
   - `requirements.txt` — shared Python dependencies
   - `.env.example` — shared environment variables

3. **For each workflow in `workflows/`:**
   - Read its `README.md` for what it does
   - Check if it has tests
   - Note its deploy target and current state

4. **Check git state** (if git is initialized)
   - `git status` — any uncommitted changes?
   - `git log -5 --oneline` — recent activity
   - Current branch

5. **Provide a summary:**
   - What this project is (standalone workflows collection)
   - How many workflows exist and their statuses (from CATALOG.md)
   - Which workflows are planned but not yet built
   - Which workflows are deployed
   - Any uncommitted changes or work in progress
   - Conventions to follow (from CLAUDE.md)
