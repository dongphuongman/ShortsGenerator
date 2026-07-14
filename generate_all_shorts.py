#!/usr/bin/env python3
"""Generate shorts for all 10 Reddit posts using the search-and-download API."""

import json
import os
import re
import requests
import subprocess
import sys
import time

BASE_DIR = "/home/leamsigc/Documents/learn/ShortsGenerator"
POSTS_DIR = os.path.join(BASE_DIR, ".reddit-research/2026-07-07_093517")
INSTAGRAM_DIR = os.path.join(BASE_DIR, "Backend/static/generated_videos/instagram")
API_URL = "http://localhost:8080/api/search-and-download"

VOICE = "M5"
AI_MODEL = "g4f"
ASPECT_RATIO = "9:16"
SUBTITLE_TEMPLATE = "classic"
SUBTITLES_POSITION = "center,bottom"
USE_MUSIC = False
THREADS = 4

def get_script_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"## Viral Video Script \(Spanish\)\n\n```\n(.+?)\n```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def get_title_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    return first_line.lstrip("# ").strip()

def get_sourced_video_urls(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    urls = re.findall(r"\]\((https?://[^\s)]+)\)", content)
    return urls

def get_search_terms(title):
    words = title.lower().split()
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "shall", "can",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "as", "into", "through", "during", "before", "after", "above",
                  "below", "between", "out", "off", "over", "under", "again",
                  "further", "then", "once", "and", "but", "or", "nor", "not",
                  "so", "yet", "both", "either", "neither", "each", "every",
                  "all", "no", "none", "any", "some", "much", "many", "more",
                  "most", "few", "fewer", "least", "less", "own", "same", "very",
                  "too", "just", "about", "up", "down", "after", "before", "this",
                  "that", "these", "those", "i", "me", "my", "myself", "we", "our",
                  "ours", "ourselves", "you", "your", "yours", "yourself",
                  "yourselves", "he", "him", "his", "himself", "she", "her",
                  "hers", "herself", "it", "its", "itself", "they", "them",
                  "their", "theirs", "themselves", "what", "which", "who", "whom",
                  "this", "that", "these", "those", "am", "are", "is", "was",
                  "were", "be", "been", "being", "have", "has", "had", "having",
                  "do", "does", "did", "doing", "would", "could", "should", "might",
                  "must", "shall", "can", "need", "dare", "ought", "used",
                  "what", "which", "who", "whom", "whose", "when", "where", "why",
                  "how", "all", "each", "every", "both", "few", "more", "most",
                  "other", "some", "such", "no", "nor", "not", "only", "own",
                  "same", "so", "than", "too", "very", "just", "because", "as",
                  "until", "while", "of", "at", "by", "for", "with", "about",
                  "against", "between", "into", "through", "during", "before",
                  "after", "above", "below", "to", "from", "up", "down", "in",
                  "out", "on", "off", "over", "under", "again", "further",
                  "then", "once", "here", "there", "when", "where", "why",
                  "how", "all", "any", "both", "each", "few", "more", "most",
                  "other", "some", "such", "no", "nor", "not", "only", "own",
                  "same", "so", "than", "too", "very", "the", "and", "but",
                  "or", "for", "yet", "nor", "so", "a", "an"}
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    return ",".join(keywords[:5]) if keywords else title

def download_video(url):
    try:
        result = subprocess.run([
            "yt-dlp", "--format", "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "-o", os.path.join(INSTAGRAM_DIR, "%(id)s.%(ext)s"),
            url
        ], capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                m = re.search(r"Merging formats into \"(.+?)\"", line)
                if m:
                    return m.group(1)
            for line in result.stderr.split("\n"):
                m = re.search(r"Merging formats into \"(.+?)\"", line)
                if m:
                    return m.group(1)
            for line in result.stdout.split("\n"):
                if "Destination:" in line:
                    path = line.split("Destination:", 1)[1].strip()
                    base = os.path.splitext(path)[0]
                    for f in os.listdir(INSTAGRAM_DIR):
                        if f.startswith(os.path.basename(base)):
                            return os.path.join(INSTAGRAM_DIR, f)
            return None
        else:
            print(f"  FAILED: {result.stderr[:200]}")
            return None
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

def find_downloaded_file(url):
    url_id = None
    for pattern in [r"watch\?v=([^&]+)", r"youtu\.be/([^?]+)", r"/video/(\d+)", r"instagram\.com/reel/([^/?]+)"]:
        m = re.search(pattern, url)
        if m:
            url_id = m.group(1)
            break
    if url_id:
        for f in os.listdir(INSTAGRAM_DIR):
            if f.startswith(url_id):
                return os.path.join(INSTAGRAM_DIR, f)
    return None

def generate_short(title, script, video_paths, search_terms):
    if not script:
        print(f"  SKIPPED: No script found")
        return False
    if not video_paths:
        print(f"  SKIPPED: No videos available")
        return False

    abs_paths = [os.path.abspath(p) for p in video_paths if os.path.exists(p)]
    if not abs_paths:
        print(f"  SKIPPED: No valid video files found")
        return False

    payload = {
        "search": search_terms,
        "script": script,
        "aiModel": AI_MODEL,
        "voice": VOICE,
        "directVideoPaths": abs_paths,
        "useMusic": USE_MUSIC,
        "subtitlesPosition": SUBTITLES_POSITION,
        "subtitleTemplate": SUBTITLE_TEMPLATE,
        "aspectRatio": ASPECT_RATIO,
        "threads": THREADS,
    }

    try:
        resp = requests.post(API_URL, json=payload, timeout=600)
        data = resp.json()
        if data.get("status") == "success":
            video_url = data.get("data", {}).get("finalVideo", "unknown")
            audio_url = data.get("data", {}).get("finalAudio", "N/A")
            print(f"  ✅ GENERATED: {video_url}")
            print(f"     Audio: {audio_url}")
            return True
        else:
            print(f"  ❌ FAILED: {data.get('message', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def main():
    md_files = sorted([f for f in os.listdir(POSTS_DIR) if f.endswith(".md") and f != "index.md"])
    results = []

    for filename in md_files:
        filepath = os.path.join(POSTS_DIR, filename)
        title = get_title_from_file(filepath)
        script = get_script_from_file(filepath)
        video_urls = get_sourced_video_urls(filepath)
        search_terms = get_search_terms(title)

        print(f"\n{'='*60}")
        print(f"📄 {filename}")
        print(f"   Title: {title}")
        print(f"   Search: {search_terms}")
        print(f"   Videos: {len(video_urls)} sourced URLs")
        print(f"   Script length: {len(script) if script else 0} chars")
        print(f"{'='*60}")

        existing_paths = []
        for url in video_urls:
            path = find_downloaded_file(url)
            if path:
                existing_paths.append(path)
                print(f"   ✅ Already downloaded: {os.path.basename(path)}")
            else:
                print(f"   ⬇️  Downloading: {url[:60]}...")
                path = download_video(url)
                if path:
                    existing_paths.append(path)
                    print(f"   ✅ Downloaded: {os.path.basename(path)}")
                else:
                    print(f"   ⚠️  Could not download: {url[:60]}...")

        if existing_paths:
            print(f"\n   🎬 Generating short with {len(existing_paths)} video(s)...")
            success = generate_short(title, script, existing_paths, search_terms)
            results.append((filename, title, success, len(existing_paths)))
        else:
            print(f"\n   ⚠️  No videos available - skipping generation")
            results.append((filename, title, False, 0))

        time.sleep(2)

    print(f"\n\n{'='*60}")
    print("📊 GENERATION SUMMARY")
    print(f"{'='*60}")
    success_count = sum(1 for r in results if r[2])
    for filename, title, success, vcount in results:
        status = "✅" if success else "❌"
        print(f"   {status} {filename} ({vcount} videos) - {title[:50]}...")
    print(f"\n   Total: {len(results)} | Success: {success_count} | Failed: {len(results) - success_count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
