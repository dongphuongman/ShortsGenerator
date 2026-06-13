# ShortsGenerator — How to Use

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites & Environment Setup](#prerequisites--environment-setup)
- [Running the Project](#running-the-project)
- [Feature Walkthrough](#feature-walkthrough)
  - [1. AI Script Generation](#1-ai-script-generation)
  - [2. Stock Video Search & Selection](#2-stock-video-search--selection)
  - [3. Text-to-Speech (TTS)](#3-text-to-speech-tts)
  - [4. Subtitle Templates & Customization](#4-subtitle-templates--customization)
  - [5. Background Music](#5-background-music)
  - [6. Aspect Ratios](#6-aspect-ratios)
  - [7. Full Video Generation Pipeline](#7-full-video-generation-pipeline)
  - [8. Generated Videos Gallery](#8-generated-videos-gallery)
  - [9. Global Settings](#9-global-settings)
  - [10. Instagram Video Downloader](#10-instagram-video-downloader)
  - [11. YouTube Auto-Upload](#11-youtube-auto-upload)
  - [12. MagicSync Social Media Scheduling](#12-magicsync-social-media-scheduling)
  - [13. Cancelling Generation](#13-cancelling-generation)
- [Automatic Posting with MagicSync + Reverse Proxy](#automatic-posting-with-magicsync--reverse-proxy)
- [Docker Setup](#docker-setup)
- [API Reference](#api-reference)

---

## Quick Start

```bash
# 1. Clone and enter the project
cd ShortsGenerator

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Copy and fill environment variables
cp .env.example .env

# 4. Install ImageMagick (Ubuntu/Debian)
sudo apt install imagemagick

# 5. Run the backend
cd Backend && python main.py

# 6. In another terminal, run the frontend
cd UI && npm install && npm run dev
```

Then open `http://localhost:3000` in your browser.

---

## Prerequisites & Environment Setup

### Required

| Variable | File | Description | How to Get |
|----------|------|-------------|-----------|
| `PEXELS_API_KEY` | `.env` | API key for stock video search | Register at https://www.pexels.com/api/ |
| `IMAGEMAGICK_BINARY` | `.env` | Path to ImageMagick `convert` binary | `which convert` (typically `/usr/bin/convert`) |
| `TIKTOK_SESSION_ID` | `.env` | TikTok session cookie for TTS | Log into TikTok in your browser, copy the `sessionid` cookie value |

### Optional

| Variable | Purpose |
|----------|---------|
| `GOOGLE_API_KEY` | Enables Gemini Pro AI model for script generation (alternative to default g4f) |
| `OPENAI_API_KEY` | Currently unused (reserved for future GPT-4 integration) |
| `ASSEMBLY_AI_API_KEY` | Enables cloud-based subtitle transcription (more accurate timing) |
| `MAGICSYNC_BASE_URL` | Default MagicSync server URL (default: `http://localhost:3000`) |
| `MAGICSYNC_API_TOKEN` | Authentication token for MagicSync API |

---

## Running the Project

### Local (Backend)

```bash
cd Backend
python main.py
# → Starts on http://0.0.0.0:8080
```

### Local (Frontend)

```bash
cd UI
npm install
npm run dev
# → Starts on http://localhost:3000
```

### Docker

```bash
docker-compose up -d
# Backend runs on port 8080
```

---

## Feature Walkthrough

### 1. AI Script Generation

The system generates viral-optimized YouTube Shorts scripts using AI. Two models are available:

- **FREE (g4f)** — Uses Gemini 2.0 Flash via the g4f library. No API key needed (default).
- **Gemini** — Uses Google's Gemini Pro directly. Requires `GOOGLE_API_KEY` in `.env`.

**How to use in the UI:**

1. Go to the **Generate** page (`/generate`)
2. Enter a **video subject** (e.g., "Why procrastination is ruining your life")
3. Optionally toggle and enter an **extra prompt** for custom instructions
4. Click **"Generate script"**
5. Review the generated script and edit it if needed
6. The system also auto-generates **5 search terms** for stock footage

**Behind the scenes:** The AI uses a carefully engineered prompt template that enforces a hook → content → payoff structure with strict rules (no markdown, conversational tone, power words, emotional triggers, 80-120 words).

**API:** `POST /api/script` with body `{videoSubject, extraPrompt, aiModel}` returns `{script, search}`.

---

### 2. Stock Video Search & Selection

Two ways to source footage:

#### a) Auto Search (default)
The AI generates search terms from your script, and the backend searches Pexels automatically for each term (15 results per term, minimum 5s duration, highest resolution selected).

#### b) Manual Search & Selection
1. Go to the **Search** page (`/search`)
2. Enter comma-separated search terms
3. Browse results with playable previews
4. Click to select/deselect specific videos
5. Use the **"Selected Videos"** tab to review your picks

#### c) Instagram as Source
1. On the **Search** page, use the **Instagram** tab
2. Enter Instagram video URLs (one per line)
3. Click download — videos are saved to `Backend/static/generated_videos/instagram/`
4. Select them just like stock videos

**Advanced:** You can also provide custom video URLs directly or pre-select video URLs to skip the search entirely.

**API:** `POST /api/search-and-download` (accepts `search`, `script`, `selectedVideoUrls`, `videoUrls` parameters).

---

### 3. Text-to-Speech (TTS)

Three TTS engines are available, configured in **Settings** (`/settings`):

| Engine | Voices | Languages | Quality | Requires |
|--------|--------|-----------|---------|----------|
| **Supertonic** (default) | 10 voices (F1-F5, M1-M5) | 33 languages | 5-12 steps | ~260MB model download on first run |
| **TikTok TTS** (fallback) | 44 voices (characters, accents, singing) | 10+ languages | N/A | `TIKTOK_SESSION_ID` |
| **KittenTTS** (alternative local) | 8 voices | English | 4 model sizes | `KITTEN_MODEL` env var |

**How to use:**

1. Go to **Settings** → **TTS Engine**
2. Choose Supertonic or TikTok
3. Select a voice, language, quality (Supertonic), and speed
4. Alternatively, select a voice directly on the **Generate** page before clicking Generate

**Health check:** Settings page shows engine status (healthy/unavailable).

**API:** `GET /api/tts/status`, `GET /api/tts/voices?engine=supertonic`, `GET /api/models`

---

### 4. Subtitle Templates & Customization

10 built-in subtitle templates:

| Template | Style | Position |
|----------|-------|----------|
| Classic Yellow | Yellow text, black stroke | Center-bottom |
| Modern Glow | White text, cyan glow | Center-center |
| Bold Outline | Thick black outline, white text | Center-bottom |
| Minimal | Small clean white text | Center-bottom |
| Cinematic | Gold text, subtle shadow | Center-bottom |
| Neon | Glowing pink neon | Center-center |
| Social Viral | High contrast orange | Center-bottom |
| Floating | Centered floating white | Center-center |
| News Ticker | Bold white, red outline | Center-top |
| Karaoke Highlight | Cyan text, magenta highlight | Center-top |

**How to use:**

1. On the **Generate** page, choose a **Subtitle Template**
2. Optionally enter **custom subtitle text** (overrides the TTS script)
3. Set **subtitle position** (center-top / center-center / center-bottom and more)
4. See a **live preview** on the phone-shaped preview

**Global customization:** Settings → Font, Color, Size, Stroke Color, Stroke Width for full control.

**API:** `GET /api/settings` returns all templates and current settings. `POST /api/settings` updates them.

---

### 5. Background Music

**How to add music to your video:**

1. On the **Generate** page, select the **Music** tab
2. Choose from the **library** (pre-loaded `.mp3` files in `Backend/static/assets/music/`)
3. Or **upload your own** audio file (mp3, wav, m4a, aac, ogg, flac, wma)
4. Or **download from a URL** (YouTube, SoundCloud, etc. — uses yt-dlp to extract audio)
5. Or extract audio from a **video URL**
6. Preview tracks with the built-in audio player
7. Click **"Add Music"** after generation to overlay audio

**How Music Upload works:** Files go to `Backend/static/assets/music/`. Downloaded audio is extracted as 192kbps MP3.

**API:** `GET /api/getSongs`, `POST /api/upload-music`, `POST /api/download-music-url`, `POST /api/addAudio`

---

### 6. Aspect Ratios

| Ratio | Label | Resolution |
|-------|-------|------------|
| 9:16 | Shorts/TikTok (default) | 1080×1920 |
| 16:9 | YouTube | 1920×1080 |
| 1:1 | Square | 1080×1080 |
| 4:5 | Instagram | 1080×1350 |
| 21:9 | Ultra Wide | 2520×1080 |

Select on the **Generate** page before generating. Also configurable as default in **Settings** → **Video Settings**.

---

### 7. Full Video Generation Pipeline

**Step-by-step on the Generate page:**

1. **Enter subject** and click **"Generate script"**
2. **Review/edit the script**
3. **Select a voice** (from the Voice tab)
4. **Choose music** (optional — from Music tab)
5. **Pick a subtitle template** (from Subtitle tab)
6. **Set aspect ratio**
7. **Adjust search terms** or **manually search and select videos**
8. **Trim video segments** by setting start/end times for each clip
9. Click **"Generate"**
10. Watch the **MultiStepLoader** showing progress:
    - ✓ Script generated
    - ✓ Search terms generated
    - ✓ Videos downloaded
    - ✓ Voice generated
    - ✓ Video combined
    - ✓ Final video rendered
11. View the result in the **Videos** gallery

**API:** `POST /api/generate` (full pipeline) or `POST /api/search-and-download` (from pre-existing script).

---

### 8. Generated Videos Gallery

Go to the **Videos** page (`/videos`) to see all generated videos in a responsive grid.

Each video card shows:
- Video playback (HTML5 player)
- Title, description, and tags (auto-generated metadata)
- **Schedule Upload** button (see MagicSync section)

Metadata is auto-generated by AI: title (under 60 chars, SEO-optimized), description (with hashtags), keywords (6 search terms). Stored as `.json` files alongside `.mp4` files.

**API:** `GET /api/getVideos`, `GET /api/video/<filename>`

---

### 9. Global Settings

Go to **Settings** (`/settings`) to configure defaults:

| Section | What You Can Set |
|---------|-----------------|
| **AI Model** | FREE (g4f) / GPT-4 / GPT-3.5 Turbo |
| **TTS Engine** | Supertonic or TikTok, with voice/language/quality/speed |
| **Font** | Font family, size, color, stroke color, stroke width |
| **Subtitles** | Default position (7 options) |
| **Video Settings** | Default aspect ratio |
| **Subtitle Templates** | Default template with descriptions |
| **Title Color** | Color swatches (12 colors) |
| **Font Options** | Dropdown of available fonts |
| **MagicSync** | URL, API token, Video Base URL |

Settings are saved to the backend and persist across sessions.

---

### 10. Instagram Video Downloader

1. Go to the **Search** page → **Instagram** tab
2. Enter Instagram video URLs (one per line)
3. Click **Download** — videos are saved to `Backend/static/generated_videos/instagram/`
4. On the **Generate** page, you can select these Instagram videos as footage

**API:** `POST /api/instagram/download` with body `{url}`.

---

### 11. YouTube Auto-Upload

**Prerequisites:**
- A Google Cloud project with the YouTube Data API v3 enabled
- OAuth 2.0 credentials downloaded as `client_secret.json`
- Place `client_secret.json` in the `Backend/` directory

**How it works:**
- When `automateYoutubeUpload` is set to `true` in the generate request
- The system authenticates via OAuth2, uploads with resumable upload (10 retries)
- Privacy is set to "private" by default, category "Science & Technology"

**Note:** This feature is currently available via API only, not directly exposed in the UI.

---

### 12. MagicSync Social Media Scheduling

MagicSync (https://magicsync.ai) is an external service that lets you schedule social media posts across multiple platforms. This project integrates with MagicSync to post generated videos automatically.

#### Setting Up MagicSync

1. **Go to Settings** → **MagicSync** section
2. Enter your **MagicSync URL** (default: `http://localhost:3000`)
3. Enter your **MagicSync API Token**
4. Enter a **Video Base URL** (see [Reverse Proxy section](#automatic-posting-with-magicsync--reverse-proxy) below)
5. Click **"Test Connection"** to verify

#### Scheduling a Post

1. Go to the **Videos** page
2. Click **"Schedule Upload"** on any video
3. Fill in the modal:
   - **Scheduled date & time** (pick a future time, or leave blank for immediate)
   - **Content** (post text)
   - **Title**
   - **Description**
   - Select **platforms** from your connected accounts
4. Click **Schedule** — the video is sent to MagicSync

**Environment variables for automation:**
```
MAGICSYNC_BASE_URL=http://localhost:3000
MAGICSYNC_API_TOKEN=your_token_here
```

**API:** `POST /api/magicsync/accounts` (list accounts), `POST /api/schedule-to-magicsync` (schedule post).

---

## Automatic Posting with MagicSync + Reverse Proxy

For MagicSync to post your videos, it needs to be able to **download the video file** from a publicly accessible URL. Since you're running the backend locally on `localhost:8080`, you need a **reverse proxy / tunnel** to expose it to the internet.

### Recommended: https://tunnl.gg/

Tunnl.gg creates a secure tunnel to your local server, giving you a public URL.

```bash
# Example with tunnl.gg (or any tunnel service) use the nuxt --tunnel is better
tunnl http://localhost:8080
# → https://your-subdomain.tunnl.gg
```

```
cd UI
npx nuxt dev  --tunnel
```
Then use the tunnel url as the base path for the assets in the configuration

### Configuration

1. Start your tunnel and get your public URL (e.g., `https://yourapp.tunnl.gg`)
2. In **Settings** → **MagicSync**, set **Video Base URL** to your tunnel URL:
   ```
   https://yourapp.tunnl.gg
   ```
3. Now when MagicSync schedules a post, it will use URLs like:
   ```
   https://yourapp.tunnl.gg/api/video/my-video.mp4
   ```
   MagicSync downloads the video from this URL and posts it to your connected platforms.

**Alternative tunnel services:** ngrok, Cloudflare Tunnel, bore, localtunnel, or any reverse proxy that exposes `localhost:8080`.

### Full MagicSync Automation Flow

```
Your Server (localhost:8080)
  └── Generate video → saved to static/generated_videos/
  └── Schedule post via MagicSync API
        └── MagicSync fetches video from:
            https://your-tunnel.tunnl.gg/api/video/my-video.mp4
              └── Posts to YouTube / TikTok / Instagram / etc.
```

---

## Docker Setup

```bash
# Build and start
docker-compose up -d

# View backend logs
docker-compose logs -f api

# Rebuild
docker-compose build --no-cache
```

The Docker setup runs the Python backend inside a container. The frontend (Nuxt) is commented out in `docker-compose.yml` — uncomment if you want to containerize it too.

---

## API Reference

### Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate` | Full end-to-end video generation |
| POST | `/api/script` | Generate script + search terms only |
| POST | `/api/search-and-download` | Generate video from existing script |
| POST | `/api/cancel` | Cancel current generation |

### Audio

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/addAudio` | Add background music to video |
| POST | `/api/upload-music` | Upload audio file to library |
| POST | `/api/download-music-url` | Download audio from URL |
| GET | `/api/getSongs` | List available music |

### Video

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/getVideos` | List generated videos with metadata |
| GET | `/api/video/<filename>` | Serve a video file |
| GET | `/api/getSubtitles` | List subtitle files |
| GET | `/api/assets` | List temp video assets |

### TTS / Voice

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | All available voices and TTS info |
| GET | `/api/tts/status` | TTS engine health check |
| GET | `/api/tts/voices` | Voices for a specific engine |

### Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings` | Get all global settings |
| POST | `/api/settings` | Update settings |

### Social

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/instagram/download` | Download Instagram video |
| POST | `/api/magicsync/accounts` | List MagicSync connected accounts |
| POST | `/api/schedule-to-magicsync` | Schedule post via MagicSync |

---
