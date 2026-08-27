---
name: reddit-research
version: 2.0.0
description: |
  Reddit content research tool — scrape top posts from any subreddit
  using Reddit's JSON API for accurate data (correct upvotes, comment
  counts), generate viral video scripts in Spanish from post content
  + top comments, search context-relevant videos, and generate
  YouTube Shorts via the short-generator skill.

allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Question
  - ChromeDevTools
  - WebSearch
  - Skill

states:
  - reddit-research-scrape    — Scrape Reddit posts via JSON API + generate scripts
  - reddit-research-generate  — Search context-relevant videos & generate Shorts
---

# Reddit Research — Main Skill (v2)

Full workflow: Scrape → Generate Shorts

## Quick Start

```
/reddit-research <subreddit> [limit:<number>]
```

Example: `/reddit-research soccer limit:10`

## Architecture

```
skills/reddit-research/          # Skill (bundled, global-installable via ~/.claude/skills/)
├── SKILL.md
└── scripts/                     # Bundled — no external .reddit-research/scripts needed
    ├── package.json
    ├── scrape.js
    └── build-csv.js

.reddit-research/               # Tool data directory (project root, auto-resolved via CWD walk-up)
└── <YYYY-MM-DD_HHMMSS>/        # One folder per research session (dated)
    ├── index.json
    ├── posts.csv
    ├── videos/
    ├── <post-slug-1>.md
    └── ...
```

**Execution model (hybrid):** the JSON API scraper and CSV builder are bundled in `skills/reddit-research/scripts/`.
Skills resolve dataRoot via CWD walk-up (`./.reddit-research`), `REDDIT_RESEARCH_ROOT`, or `--data-root`. Global-install safe.
Use the Chrome DevTools CLI for DuckDuckGo video searches (Phase 2) where convenient.
Script generation uses the local Flask backend on port 8080 (preserved).

## Workflow

### Phase 1: Scrape Reddit (`skill reddit-research-scrape`)

1. Ask user for subreddit, post count, sort order, script language
2. Run: `node "$CLAUDE_SKILL_ROOT/scripts/scrape.js" <subreddit> <limit> <sort> <lang>  # fallback: node ./skills/reddit-research/scripts/scrape.js ...`
   - Fetches the listing + each post via the **JSON API** for **correct data**
     (accurate upvotes, comment counts, full comments, exact selftext)
   - Generates a **viral video script** via the backend API (post + top 10 comments)
   - Saves one `<post-slug>.md` per post + `index.json`

### Phase 2: Generate Shorts (`skill reddit-research-generate`) ask the user if they want to generate Shorts

1. Read all saved post files from `.reddit-research/<timestamp>/`
2. For each post, search DuckDuckGo/WebSearch for **context-relevant videos**
   - Query is SPECIFIC to the post topic (not generic)
   - E.g., for a Klopp post: `"Jürgen Klopp German national team new era coach 2026"`
3. Append video URLs to each post's markdown file
4. Call `/short-generator` for each post with:
   - Subject: post title
   - Script: the pre-generated viral script from the markdown file
   - Voice: M5
   - Subtitle position: center,bottom
   - Direct video URLs from the search

### Phase 3: Generate CSV for MagicSync Bulk Scheduling (ask the user if they want to generate CSV)

After Phase 2 (and after asking the user), generate a CSV ready for MagicSync import.

```bash
node "$CLAUDE_SKILL_ROOT/scripts/build-csv.js" <timestamp>
# fallback: node ./skills/reddit-research/scripts/build-csv.js <timestamp>
```

The script:
1. Generates a social media post for each post (Flask backend, or falls back to the viral script)
2. Validates image/video URLs by content-type (priority: post video → sourced videos → linked URL)
3. Downloads video files locally to `videos/` (leaves `image_url` empty for those)
4. Calculates optimal US scheduling times and builds `posts.csv`

**CSV columns (only):** `content,image_url,scheduled_time` — no `comments` column.
`content` = escaped post text; `image_url` = valid https image (empty for video posts); `scheduled_time` = ISO 8601 UTC.

## Output Structure

```
.reddit-research/
  └── <YYYY-MM-DD_HHMMSS>/
      ├── index.json                    # Summary with correct upvotes/comment counts
      ├── posts.csv                     # MagicSync-ready CSV (Phase 3)
      ├── videos/                       # Locally downloaded videos (Phase 3)
      │   ├── <post-slug-1>.mp4
      │   └── <post-slug-2>.mp4
      ├── <post-slug-1>.md              # Title, content, script, social post, videos, comments
      ├── <post-slug-2>.md
      └── ...
```

## Key v2 Improvements

| Feature | v1 | v2 |
|---------|----|----|
| Data source | HTML scraping (buggy upvotes) | **JSON API** (correct data) |
| Upvotes | Often showed `1` | Real count (e.g., 3105) |
| Comment count | Missing | Real count (e.g., 346) |
| Comments | Author/score missing | All fields present |
| Video script | Not generated | **Auto-generated from post + top comments** |
| Video search | Generic queries | **Topic-specific queries** |
| Script language | English | **Spanish** (configurable) |

## Example: Post 1 Before vs After (r/soccer)

**Before (v1 HTML scrape)**:
- Upvotes: `1` ← wrong
- Comments: missing
- Script: none
- Video search: generic "soccer video"

**After (v2 JSON API)**:
- Upvotes: `3105` ← correct
- Comments: `346` ← correct
- Script: Spanish viral script using top comments
- Social media post: Spanish viral Social media post with a viral hook spcifically targeting facebook and instagram and a image url will be desired
- Video search: "Jürgen Klopp German national team new era coach 2026"
