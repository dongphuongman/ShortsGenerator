#!/bin/bash
# =============================================================================
# Social Media Research — Transcribe audio files using Whisper
# Platform-agnostic: works with any audio from any platform
# Processes all audio files in transcripts/ that don't have a matching .txt
# Usage: bash scripts/transcribe.sh <project-name> [sessionId] [--session <id>] [--data-root <path>]
# =============================================================================

PROJECT=""
SESSION=""
DATA_ROOT=""

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

resolve_data_root() {
  local dot=".ig-research"
  if [[ -n "$DATA_ROOT" ]]; then echo "$DATA_ROOT"; return; fi
  if [[ -n "$IG_RESEARCH_ROOT" ]]; then echo "$IG_RESEARCH_ROOT"; return; fi
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
  LATEST_TS=$(ls -1 "$PROJECT_DIR" 2>/dev/null | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}$' | sort | tail -n 1)
  if [[ -n "$LATEST_TS" ]]; then
    SESSION_DIR="$PROJECT_DIR/$LATEST_TS"
  else
    SESSION_DIR="$PROJECT_DIR"
  fi
fi

TRANSCRIPTS_DIR="$SESSION_DIR/transcripts"
if [[ ! -d "$TRANSCRIPTS_DIR" && -d "$PROJECT_DIR/transcripts" ]]; then
  TRANSCRIPTS_DIR="$PROJECT_DIR/transcripts"
  SESSION_DIR="$PROJECT_DIR"
fi

if [[ ! -d "$TRANSCRIPTS_DIR" ]]; then
  echo "No transcripts directory found for project: $PROJECT (session: $SESSION_DIR)"
  echo "Looked in: $TRANSCRIPTS_DIR and $PROJECT_DIR/transcripts"
  exit 1
fi

AUDIO_FILES=$(find "$TRANSCRIPTS_DIR" -name "*.mp3" -o -name "*.m4a" -o -name "*.webm" -o -name "*.opus" | sort)
TOTAL=$(echo "$AUDIO_FILES" | grep -c "." || true)

if [[ "$TOTAL" -eq 0 ]]; then
  echo "No audio files to transcribe."
  exit 0
fi

echo ""
echo "========================================"
echo "  Transcribing $TOTAL audio files"
echo "  Project: $PROJECT"
echo "  Session: $SESSION_DIR"
echo "========================================"
echo ""

DONE=0
SKIPPED=0

for AUDIO in $AUDIO_FILES; do
  FILENAME=$(basename "$AUDIO")
  BASENAME="${FILENAME%.*}"
  TXT_FILE="$TRANSCRIPTS_DIR/$BASENAME.txt"

  if [[ -f "$TXT_FILE" ]]; then
    SKIPPED=$((SKIPPED + 1))
    continue
  fi

  DONE=$((DONE + 1))
  echo "  [$DONE/$TOTAL] $BASENAME..."

  python3 -m whisper "$AUDIO" \
    --model tiny \
    --language en \
    --output_format txt \
    --output_dir "$TRANSCRIPTS_DIR" \
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
echo "  Transcribed: $DONE"
echo "  Skipped (already done): $SKIPPED"
echo "  Output: $TRANSCRIPTS_DIR"
echo "========================================"
