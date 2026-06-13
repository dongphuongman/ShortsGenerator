import os
import numpy as np
import soundfile as sf
from typing import List, Dict, Optional
from termcolor import colored

VOICE_STYLES = {
    "F1": {"name": "Sarah", "description": "Calm female voice with slightly low tone; steady and composed", "gender": "female"},
    "F2": {"name": "Lily", "description": "Bright, cheerful female voice; lively, playful, youthful", "gender": "female"},
    "F3": {"name": "Jessica", "description": "Clear, professional announcer-style female voice; articulate, broadcast-ready", "gender": "female"},
    "F4": {"name": "Olivia", "description": "Crisp, confident female voice; distinct, expressive, strong delivery", "gender": "female"},
    "F5": {"name": "Emily", "description": "Kind, gentle female voice; soft-spoken, calm, naturally soothing", "gender": "female"},
    "M1": {"name": "Alex", "description": "Lively, upbeat male voice with confident energy, clear tone", "gender": "male"},
    "M2": {"name": "James", "description": "Deep, robust male voice; calm, composed, serious", "gender": "male"},
    "M3": {"name": "Robert", "description": "Polished, authoritative male voice; confident, trustworthy", "gender": "male"},
    "M4": {"name": "Sam", "description": "Soft, neutral-toned male voice; gentle, approachable, youthful", "gender": "male"},
    "M5": {"name": "Daniel", "description": "Warm, soft-spoken male voice; calm, soothing, storytelling", "gender": "male"},
}

LANGUAGES = [
    {"code": "na", "label": "Language-Agnostic"},
    {"code": "en", "label": "English"},
    {"code": "es", "label": "Spanish"},
    {"code": "pt", "label": "Portuguese"},
    {"code": "fr", "label": "French"},
    {"code": "de", "label": "German"},
    {"code": "it", "label": "Italian"},
    {"code": "nl", "label": "Dutch"},
    {"code": "ru", "label": "Russian"},
    {"code": "ko", "label": "Korean"},
    {"code": "ja", "label": "Japanese"},
    {"code": "zh", "label": "Chinese"},
    {"code": "ar", "label": "Arabic"},
    {"code": "bg", "label": "Bulgarian"},
    {"code": "cs", "label": "Czech"},
    {"code": "da", "label": "Danish"},
    {"code": "el", "label": "Greek"},
    {"code": "et", "label": "Estonian"},
    {"code": "fi", "label": "Finnish"},
    {"code": "hi", "label": "Hindi"},
    {"code": "hr", "label": "Croatian"},
    {"code": "hu", "label": "Hungarian"},
    {"code": "id", "label": "Indonesian"},
    {"code": "lt", "label": "Lithuanian"},
    {"code": "lv", "label": "Latvian"},
    {"code": "pl", "label": "Polish"},
    {"code": "ro", "label": "Romanian"},
    {"code": "sk", "label": "Slovak"},
    {"code": "sl", "label": "Slovenian"},
    {"code": "sv", "label": "Swedish"},
    {"code": "tr", "label": "Turkish"},
    {"code": "uk", "label": "Ukrainian"},
    {"code": "vi", "label": "Vietnamese"},
]

QUALITY_PRESETS = [
    {"value": 5, "label": "Fast (Low Quality)"},
    {"value": 6, "label": "Quick"},
    {"value": 7, "label": "Balanced"},
    {"value": 8, "label": "Standard (Default)"},
    {"value": 9, "label": "High Quality"},
    {"value": 10, "label": "Enhanced"},
    {"value": 11, "label": "Premium"},
    {"value": 12, "label": "Maximum (Best Quality)"},
]

SUPPORTED_LANGUAGE_CODES = {lang["code"] for lang in LANGUAGES}

_tts_instance = None


def _get_tts():
    global _tts_instance
    if _tts_instance is None:
        from supertonic import TTS
        print(colored("[+] Initializing Supertonic TTS model (first run downloads ~260MB)...", "cyan"))
        _tts_instance = TTS(auto_download=True)
        print(colored("[+] Supertonic TTS model loaded", "green"))
    return _tts_instance


def get_voice_style(voice_name: str):
    tts = _get_tts()
    return tts.get_voice_style(voice_name=voice_name)


def tts(
    text: str,
    voice: str = "M3",
    lang: str = "en",
    total_steps: int = 8,
    speed: float = 1.05,
    filename: str = "output.wav"
) -> str:
    if not text:
        raise ValueError("Text cannot be empty")

    if voice not in VOICE_STYLES:
        raise ValueError(f"Invalid voice: {voice}. Available: {', '.join(VOICE_STYLES.keys())}")

    tts = _get_tts()
    style = tts.get_voice_style(voice_name=voice)

    wav, duration = tts.synthesize(
        text=text,
        lang=lang,
        voice_style=style,
        total_steps=total_steps,
        speed=speed,
    )

    audio_data = wav.squeeze()
    sample_rate = 44100
    sf.write(filename, audio_data, sample_rate)
    print(colored(f"[+] Supertonic audio saved to '{filename}' ({duration[0]:.2f}s)", "green"))
    return filename


def available_voices() -> List[str]:
    return list(VOICE_STYLES.keys())


def available_voices_detailed() -> Dict[str, dict]:
    return VOICE_STYLES


def available_languages() -> List[Dict]:
    return LANGUAGES


def available_quality_presets() -> List[Dict]:
    return QUALITY_PRESETS


def is_supertonic_available() -> bool:
    try:
        _get_tts()
        return True
    except Exception as e:
        print(colored(f"[-] Supertonic check failed: {e}", "red"))
        return False