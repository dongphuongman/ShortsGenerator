#!/bin/bash
# =============================================================================
# Facebook Research — Transcribe downloaded reels with Whisper
# Processes video files in video-template/downloads/ and writes .txt + .srt
# to video-template/transcripts/. Skips files already transcribed.
# Usage: bash scripts/transcribe.sh <project-name> [sessionId] [--session <id>] [--data-root <path>]
#   Resolves data root via FB_RESEARCH_ROOT, CWD walk-up, or --data-root.
#   If sessionId given, uses projects/<name>/<session>/video-template/; else latest.
# =============================================================================

PROJECT=""
SESSION=""
DATA_ROOT=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="$2"; shift 2;;
    --session=*) SESSION="${1#*=}"; shift;;
    --data-root) DATA_ROOT="$2"; shift 2;;
    --data-root=*) DATA_ROOT="${1#*=}"; shift;;
    --*) shift;;
    *) if [[ -z "$PROJECT" ]]; then PROJECT="$1"; elif [[ -z "$SESSION" ]]; then SESSION="$1"; fi; shift;;
  esac
done

if [[ -z "$PROJECT" ]]; then
  echo "Usage: bash scripts/transcribe.sh <project-name> [sessionId] [--session <id>] [--data-root <path>]"
  exit 1
fi

# Resolve data root
resolve_data_root() {
  local dot=".fb-research"
  if [[ -n "$DATA_ROOT" ]]; then echo "$DATA_ROOT"; return; fi
  if [[ -n "$FB_RESEARCH_ROOT" ]]; then echo "$FB_RESEARCH_ROOT"; return; fi
  local dir="$(pwd)"
  while true; do
    if [[ -d "$dir/$dot" ]]; then echo "$dir/$dot"; return; fi
    local parent="$(dirname "$dir")"
    if [[ "$parent" == "$dir" ]]; then break; fi
    dir="$parent"
  done
  echo "$(pwd)/$dot"
}

DATA_ROOT_RESOLVED="$(resolve_data_root)"
PROJECT_DIR="$DATA_ROOT_RESOLVED/projects/$PROJECT"

# Resolve session dir
SESSION_DIR=""
if [[ -n "$SESSION" ]]; then
  SESSION_DIR="$PROJECT_DIR/$SESSION"
elif [[ -f "$PROJECT_DIR/latest.json" ]]; then
  LATEST_SESSION=$(python3 -c "import json; print(json.load(open('$PROJECT_DIR/latest.json')).get('sessionId',''))" 2>/dev/null)
  if [[ -n "$LATEST_SESSION" && -d "$PROJECT_DIR/$LATEST_SESSION" ]]; then
    SESSION_DIR="$PROJECT_DIR/$LATEST_SESSION"
  fi
fi
if [[ -z "$SESSION_DIR" || ! -d "$SESSION_DIR" ]]; then
  # fallback: latest timestamp dir
  LATEST_TS=$(ls -1 "$PROJECT_DIR" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}$' | sort | tail -n 1)
  if [[ -n "$LATEST_TS" ]]; then
    SESSION_DIR="$PROJECT_DIR/$LATEST_TS"
  else
    SESSION_DIR="$PROJECT_DIR"
  fi
fi

DOWNLOAD_DIR="$SESSION_DIR/video-template/downloads"
OUT_DIR="$SESSION_DIR/video-template/transcripts"

# Fallback to projectDir legacy if session dir has no downloads but projectDir does
if [[ ! -d "$DOWNLOAD_DIR" && -d "$PROJECT_DIR/video-template/downloads" ]]; then
  DOWNLOAD_DIR="$PROJECT_DIR/video-template/downloads"
  OUT_DIR="$PROJECT_DIR/video-template/transcripts"
  SESSION_DIR="$PROJECT_DIR"
fi

if [[ ! -d "$DOWNLOAD_DIR" ]]; then
  echo "No downloads directory found for project: $PROJECT (session: $SESSION_DIR) (run download-reels first)"
  echo "Looked in: $DOWNLOAD_DIR and $PROJECT_DIR/video-template/downloads"
  exit 1
fi

mkdir -p "$OUT_DIR"

VIDEO_FILES=$(find "$DOWNLOAD_DIR" -type f \( -name "*.mp4" -o -name "*.webm" -o -name "*.mov" \) | sort)
TOTAL=$(echo "$VIDEO_FILES" | grep -c "." || true)

if [[ "$TOTAL" -eq 0 ]]; then
  echo "No video files to transcribe."
  exit 0
fi

echo ""
echo "========================================"
echo "  Transcribing $TOTAL video files"
echo "  Project: $PROJECT"
echo "  Session: $SESSION_DIR"
echo "========================================"
echo ""

DONE=0
SKIPPED=0

for VIDEO in $VIDEO_FILES; do
  BASENAME=$(basename "$VIDEO" | sed 's/\.[^.]*$//')
  TXT_FILE="$OUT_DIR/$BASENAME.txt"

  if [[ -f "$TXT_FILE" ]]; then
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  DONE=$((DONE + 1))
  echo "  [$DONE/$TOTAL] $BASENAME..."

  python3 -m whisper "$VIDEO" \
    --model base \
    --language es \
    --output_format all \
    --output_dir "$OUT_DIR" \
    --fp16 False \
    --verbose False \
    2>/dev/null

  if [[ -f "$TXT_FILE" ]]; then
    echo "    ok ($(wc -w < "$TXT_FILE" | tr -d ' ') words)"
  else
    echo "    FAILED"
  fi
done

echo ""
echo "========================================"
echo "  Transcription complete!"
echo "  Transcribed: $DONE | Skipped: $SKIPPED"
echo "  Output: $OUT_DIR"
echo "========================================"
