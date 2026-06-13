import os
import soundfile as sf
from typing import List
from termcolor import colored

VOICES = [
    "Bella",
    "Jasper",
    "Luna",
    "Bruno",
    "Rosie",
    "Hugo",
    "Kiki",
    "Leo",
]

_kitten_model = None


def _get_model():
    global _kitten_model
    if _kitten_model is None:
        from kittentts import KittenTTS
        model_size = os.environ.get("KITTEN_MODEL", "nano-0.8-int8")
        _kitten_model = KittenTTS(f"KittenML/kitten-tts-{model_size}")
    return _kitten_model


AVAILABLE_MODELS = {
    "mini": "KittenML/kitten-tts-mini-0.8",
    "micro": "KittenML/kitten-tts-micro-0.8",
    "nano": "KittenML/kitten-tts-nano-0.8",
    "nano-int8": "KittenML/kitten-tts-nano-0.8-int8",
}


def tts(text: str, voice: str, filename: str = "output.wav") -> None:
    if not text:
        raise ValueError("Text cannot be empty")

    if voice not in VOICES:
        raise ValueError(f"Invalid voice: {voice}. Available voices: {VOICES}")

    model = _get_model()
    audio = model.generate(text, voice=voice, speed=1.0)

    if isinstance(audio, tuple):
        audio_data, sample_rate = audio
    else:
        audio_data = audio
        sample_rate = 24000

    sf.write(filename, audio_data, sample_rate)
    print(colored(f"[+] KittenTTS audio saved to '{filename}'", "green"))


def available_voices() -> List[str]:
    return VOICES


def is_kitten_available() -> bool:
    try:
        _get_model()
        return True
    except Exception:
        return False
