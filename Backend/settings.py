# Create global settings to save the following

import requests
from termcolor import colored


fontSettings = {
    "font": "static/assets/fonts/bold_font.ttf",
    "fontsize": 100,
    "color": "#FFFF00",
    "stroke_color": "black",
    "stroke_width": 5,
    "subtitles_position": "center,bottom",
}

# Video Aspect Ratio Settings
aspectRatioSettings = {
    "current": "9:16",
    "options": [
        {"value": "9:16", "label": "9:16 (Shorts/TikTok)", "width": 1080, "height": 1920},
        {"value": "16:9", "label": "16:9 (YouTube)", "width": 1920, "height": 1080},
        {"value": "1:1", "label": "1:1 (Square)", "width": 1080, "height": 1080},
        {"value": "4:5", "label": "4:5 (Instagram)", "width": 1080, "height": 1350},
        {"value": "21:9", "label": "21:9 (Ultra Wide)", "width": 2520, "height": 1080},
    ]
}

# Title Color Options
titleColorSettings = {
    "current": "#FFFF00",
    "options": [
        {"value": "#FFFF00", "label": "Yellow (Classic)", "sample": "text-yellow-400"},
        {"value": "#FF0000", "label": "Red", "sample": "text-red-500"},
        {"value": "#00FF00", "label": "Green", "sample": "text-green-400"},
        {"value": "#00FFFF", "label": "Cyan", "sample": "text-cyan-400"},
        {"value": "#FF00FF", "label": "Magenta", "sample": "text-fuchsia-400"},
        {"value": "#FFFFFF", "label": "White", "sample": "text-white"},
        {"value": "#000000", "label": "Black", "sample": "text-black"},
        {"value": "#FF6B00", "label": "Orange", "sample": "text-orange-500"},
        {"value": "#00FF7F", "label": "Spring Green", "sample": "text-green-300"},
        {"value": "#FFD700", "label": "Gold", "sample": "text-yellow-300"},
        {"value": "#FF1493", "label": "Deep Pink", "sample": "text-pink-500"},
        {"value": "#7B68EE", "label": "Medium Slate Blue", "sample": "text-indigo-400"},
    ]
}

# Font Options
fontOptions = {
    "current": "bold_font.ttf",
    "options": [
        {"value": "bold_font.ttf", "label": "Bold (Default)"},
        {"value": "Arimo-Regular.ttf", "label": "Arimo Regular"},
        {"value": "Roboto-Bold.ttf", "label": "Roboto Bold"},
        {"value": "OpenSans-Bold.ttf", "label": "OpenSans Bold"},
        {"value": "Montserrat-Bold.ttf", "label": "Montserrat Bold"},
        {"value": "Poppins-Bold.ttf", "label": "Poppins Bold"},
        {"value": "Oswald-Bold.ttf", "label": "Oswald Bold"},
        {"value": "Raleway-Bold.ttf", "label": "Raleway Bold"},
    ]
}

# Subtitle Templates
subtitleTemplates = {
    "current": "classic",
    "options": [
        {
            "value": "classic",
            "label": "Classic Yellow",
            "description": "Yellow text with black stroke",
            "color": "#FFFF00",
            "stroke_color": "black",
            "stroke_width": 5,
            "fontsize": 100,
            "position": "center,bottom"
        },
        {
            "value": "modern_glow",
            "label": "Modern Glow",
            "description": "White text with colored glow effect",
            "color": "#FFFFFF",
            "stroke_color": "#00FFFF",
            "stroke_width": 3,
            "fontsize": 90,
            "position": "center,center"
        },
        {
            "value": "bold_outline",
            "label": "Bold Outline",
            "description": "Thick black outline, white text",
            "color": "#FFFFFF",
            "stroke_color": "black",
            "stroke_width": 8,
            "fontsize": 110,
            "position": "center,bottom"
        },
        {
            "value": "minimal",
            "label": "Minimal",
            "description": "Small clean white text",
            "color": "#FFFFFF",
            "stroke_color": "black",
            "stroke_width": 2,
            "fontsize": 60,
            "position": "center,bottom"
        },
        {
            "value": "cinematic",
            "label": "Cinematic",
            "description": "Gold text with subtle shadow",
            "color": "#FFD700",
            "stroke_color": "black",
            "stroke_width": 4,
            "fontsize": 80,
            "position": "center,bottom"
        },
        {
            "value": "neon",
            "label": "Neon",
            "description": "Glowing pink neon effect",
            "color": "#FF00FF",
            "stroke_color": "#FF1493",
            "stroke_width": 3,
            "fontsize": 95,
            "position": "center,center"
        },
        {
            "value": "social_viral",
            "label": "Social Viral",
            "description": "High contrast for maximum engagement",
            "color": "#FF6B00",
            "stroke_color": "black",
            "stroke_width": 6,
            "fontsize": 105,
            "position": "center,bottom"
        },
        {
            "value": "floating",
            "label": "Floating",
            "description": "Centered floating text",
            "color": "#FFFFFF",
            "stroke_color": "#000000",
            "stroke_width": 4,
            "fontsize": 85,
            "position": "center,center"
        },
        {
            "value": "news_ticker",
            "label": "News Ticker",
            "description": "Top-anchored bold white text with red outline",
            "color": "#FFFFFF",
            "stroke_color": "#FF0000",
            "stroke_width": 5,
            "fontsize": 75,
            "position": "center,top"
        },
        {
            "value": "karaoke_highlight",
            "label": "Karaoke Highlight",
            "description": "Top-anchored cyan text with magenta highlight",
            "color": "#00FFFF",
            "stroke_color": "#FF00FF",
            "stroke_width": 4,
            "fontsize": 95,
            "position": "center,top"
        },
    ]
}


scriptSettings = {
    "defaultPromptStart":
        """
# Role: Viral YouTube Shorts Script Generator

## GOAL:
Create a HIGHLY ENGAGING, VIRAL-WORTHY 60-second video script that keeps viewers hooked from the FIRST SECOND until the end.

## VIRAL VIDEO FORMULA - MUST FOLLOW:

### 1. THE HOOK (0-3 seconds)
- Start with a SHOCKING statement, controversial take, or unexpected fact
- Use words like "Nobody tells you", "The truth about", "I wish I knew", "Stop doing"
- Create immediate curiosity gap - make them NEED to know more

### 2. THE CONTENT (3-45 seconds)
- Deliver VALUABLE, ACTIONABLE content
- Use SHORT, PUNCHY sentences (5-10 words max per segment)
- Include 2-3 "pattern interrupts" - unexpected shifts in content or tone
- Build TENSION - create questions in viewer's mind that you WILL answer

### 3. THE PAYOFF (45-60 seconds)
- Deliver the ANSWER or SOLUTION they came for
- End with a CALL TO ACTION: "Follow for more", "Save this", "Share with a friend"
- Leave them wanting MORE - create curiosity for next video

## STRICT RULES:
1. NO markdown, NO titles, NO formatting - pure raw script
2. NO introductions like "In this video" or "Welcome back"
3. NO "voiceover" or "narrator" labels
4. Write in CONVERSATIONAL, COLLOQUIAL tone - like talking to a friend
5. Use POWER WORDS: Secret, Truth, Hack, Trick, Mistake, Never, Always, Everyone, Nobody
6. Include EMOTIONAL TRIGGERS: surprise, curiosity, FOMO, amusement
7. Respond in the SAME LANGUAGE as the video subject
8. Keep TOTAL script length around 80-120 words for 60-second video

## SUBJECT:
""",
    "defaultPromptEnd":
        """
## FINAL REMINDERS:
- NO markdown, NO formatting, NO titles
- Pure raw script text only
- Start with a BANG - no boring introductions
- Every sentence must ADD VALUE or CREATE CURIOSITY
- End with engagement hook
- Write like you're telling a SECRET to a friend
"""
}

ttsSettings = {
    "preferred_tts": "supertonic",
    "tts_voice": "M3",
    "tts_lang": "en",
    "tts_quality": 8,
    "tts_speed": 1.05,
}


def get_tts_settings() -> dict:
    return ttsSettings


def update_tts_settings(new_settings: dict) -> None:
    ttsSettings.update(new_settings)


def get_tts_engine() -> str:
    return ttsSettings.get("preferred_tts", "supertonic")


def get_supertonic_voices() -> list:
    from supertonic_tts import available_voices
    return available_voices()


def get_supertonic_voices_detailed() -> dict:
    from supertonic_tts import available_voices_detailed
    return available_voices_detailed()


def get_supertonic_languages() -> list:
    from supertonic_tts import available_languages
    return available_languages()


def get_supertonic_quality_presets() -> list:
    from supertonic_tts import available_quality_presets
    return available_quality_presets()


def get_tiktok_voices() -> list:
    from tiktokvoice import available_voices
    return available_voices()


def get_all_voices() -> dict:
    return {
        "supertonic": get_supertonic_voices(),
        "tiktok": get_tiktok_voices(),
    }


def is_supertonic_available() -> bool:
    try:
        from supertonic_tts import is_supertonic_available
        return is_supertonic_available()
    except Exception:
        return False


def is_tiktok_available() -> bool:
    return True


def get_tts_status() -> dict:
    return {
        "supertonic": "healthy" if is_supertonic_available() else "unavailable",
        "tiktok": "available" if is_tiktok_available() else "unavailable",
    }


def tts_with_fallback(text: str, voice: str, filename: str, **kwargs) -> dict:
    engine = get_tts_engine()
    result = {"engine": engine, "success": False, "error": None}

    if engine == "supertonic":
        try:
            from supertonic_tts import tts as supertonic_tts
            lang = kwargs.get("lang", ttsSettings.get("tts_lang", "en"))
            quality = kwargs.get("quality", ttsSettings.get("tts_quality", 8))
            speed = kwargs.get("speed", ttsSettings.get("tts_speed", 1.05))
            supertonic_tts(text, voice=voice, lang=lang, total_steps=quality, speed=speed, filename=filename)
            result["success"] = True
            print(colored("[+] Used Supertonic TTS", "green"))
            return result
        except Exception as e:
            print(colored(f"[-] Supertonic TTS failed: {e}", "yellow"))
            print(colored("[*] Falling back to TikTokTTS", "yellow"))

    try:
        from tiktokvoice import tts as tiktok_tts
        tiktok_tts(text, voice, filename)
        result["engine"] = "tiktok"
        result["success"] = True
        print(colored("[+] Used TikTokTTS (fallback)", "green"))
        return result
    except Exception as e:
        result["error"] = str(e)
        print(colored(f"[-] Both TTS engines failed: {e}", "red"))
        return result


def get_settings() -> dict:
    """ 
    Return the global settings  
    The script settings are:
        defaultPromptStart: Start of the prompt
        defaultPromptEnd: End of the prompt
    The Subtitle settings are:
        font: font path,
        fontsize: font size,
        color: Hexadecimal color,
        stroke_color: color of the stroke,
        stroke_width: Number of pixels of the stroke
        subtitles_position: Position of the subtitles
    The TTS settings are:
        preferred_tts: "supertonic" or "tiktok"
        tts_voice: voice style (e.g. "M3")
        tts_lang: language code (e.g. "en")
        tts_quality: quality steps 5-12
        tts_speed: speed 0.7-2.0
    The Aspect Ratio settings are:
        current: current aspect ratio
        options: list of available aspect ratios
    The Title Color settings are:
        current: current color
        options: list of available colors
    The Font Options settings are:
        current: current font
        options: list of available fonts
    The Subtitle Templates settings are:
        current: current template
        options: list of predefined templates
    """
    # Return the global settings
    return {
        "scriptSettings": scriptSettings,
        "fontSettings": fontSettings,
        "ttsSettings": ttsSettings,
        "aspectRatioSettings": aspectRatioSettings,
        "titleColorSettings": titleColorSettings,
        "fontOptions": fontOptions,
        "subtitleTemplates": subtitleTemplates,
    }

# Update the global settings
def update_settings(new_settings: dict, settingType="FONT"):
    """
    Update the global settings
    The script settings are:
        defaultPromptStart: Start of the prompt
        defaultPromptEnd: End of the prompt
    The Subtitle settings are:
        font: font path,
        fontsize: font size,
        color: Hexadecimal color,
        stroke_color: color of the stroke,
        stroke_width: Number of pixels of the stroke
        subtitles_position: Position of the subtitles
    The TTS settings are:
        preferred_tts: "supertonic" or "tiktok"
        tts_voice: voice style (e.g. "M3")
        tts_lang: language code (e.g. "en")
        tts_quality: quality steps 5-12
        tts_speed: speed 0.7-2.0
    
    Args:
        new_settings (dict): The new settings to update
        settingType (str, optional): The type of setting to update. Defaults to "FONT" OR "SCRIPT" OR "TTS".
    """
    # Update the global
    if settingType == "FONT":
        fontSettings.update(new_settings)
    elif settingType == "SCRIPT":
        scriptSettings.update(new_settings)
    elif settingType == "TTS":
        ttsSettings.update(new_settings)
    elif settingType == "ASPECT":
        aspectRatioSettings.update(new_settings)
    elif settingType == "TITLE_COLOR":
        titleColorSettings.update(new_settings)
    elif settingType == "FONT_OPTIONS":
        fontOptions.update(new_settings)
    elif settingType == "SUBTITLE_TEMPLATE":
        subtitleTemplates.update(new_settings)