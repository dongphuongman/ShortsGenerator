import os
import re
import uuid
import json
import subprocess
import requests
import srt_equalizer
import assemblyai as aai
from uuid import uuid4


from settings import *

# Fix PIL compatibility: ANTIALIAS was removed in Pillow 10+
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
from typing import List, Optional
from moviepy.editor import *
from termcolor import colored
from dotenv import load_dotenv
from datetime import timedelta
from moviepy.video.fx.all import crop
from moviepy.video.tools.subtitles import SubtitlesClip

load_dotenv("../.env")

ASSEMBLY_AI_API_KEY = os.getenv("ASSEMBLY_AI_API_KEY")


def save_video(video_url: str, directory: str = "static/assets/temp") -> str:
    os.makedirs(directory, exist_ok=True)

    video_id = uuid.uuid4()
    video_path = os.path.join(directory, f"{video_id}.mp4")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
    }

    try:
        response = requests.get(video_url, headers=headers, stream=True)
        response.raise_for_status()

        with open(video_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return video_path

    except requests.exceptions.RequestException as e:
        print(f"Error downloading the video: {e}")
        return None
    except Exception as e:
        print(f"Error processing the video: {e}")
        return None


def __generate_subtitles_assemblyai(audio_path: str, voice: str) -> str:
    language_mapping = {
        "br": "pt",
        "id": "en",
        "jp": "ja",
        "kr": "ko",
    }

    if voice in language_mapping:
        lang_code = language_mapping[voice]
    else:
        lang_code = voice

    aai.settings.api_key = ASSEMBLY_AI_API_KEY
    config = aai.TranscriptionConfig(language_code=lang_code)
    transcriber = aai.Transcriber(config=config)
    transcript = transcriber.transcribe(audio_path)
    subtitles = transcript.export_subtitles_srt()

    return subtitles


def __generate_subtitles_locally(audio_path: str, sentences: List[str], voice: str, sentence_durations: Optional[List[float]] = None) -> str:
    def convert_to_srt_time_format(total_seconds):
        if total_seconds < 0:
            total_seconds = 0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        millis = int(round((total_seconds - int(total_seconds)) * 1000))
        if millis == 1000:
            millis = 0
            seconds += 1
        if seconds == 60:
            seconds = 0
            minutes += 1
        if minutes == 60:
            minutes = 0
            hours += 1
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    try:
        probe_clip = AudioFileClip(audio_path)
        total_duration = float(probe_clip.duration)
        probe_clip.close()
    except Exception as e:
        print(colored(f"[-] Could not probe audio for subtitle timing: {e}", "yellow"))
        total_duration = max(1.0, len(sentences) * 3.0)

    if not sentences:
        return ""

    cursor = 0.0
    subtitles = []
    for i, sentence in enumerate(sentences, start=1):
        if sentence_durations and i - 1 < len(sentence_durations):
            share = sentence_durations[i - 1]
        else:
            s_clean = sentence.strip()
            weight = max(1.0, len(s_clean.split()) if s_clean else 1.0)
            total_weight = sum(max(1.0, len(s.strip().split())) for s in sentences if s.strip())
            share = (weight / max(total_weight, 1.0)) * total_duration
        end_time = cursor + share
        if i == len(sentences):
            end_time = total_duration
        subtitle_entry = (
            f"{i}\n"
            f"{convert_to_srt_time_format(cursor)} --> {convert_to_srt_time_format(end_time)}\n"
            f"{sentence.strip()}\n"
        )
        subtitles.append(subtitle_entry)
        cursor = end_time

    return "\n".join(subtitles)


def generate_subtitles(audio_path: str, sentences: List[str], voice: str, sentence_durations: Optional[List[float]] = None) -> str:
    def equalize_subtitles(srt_path: str, max_chars: int = 42) -> None:
        srt_equalizer.equalize_srt_file(srt_path, srt_path, max_chars)

    subtitles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "subtitles"))
    subtitles_path = os.path.join(subtitles_dir, f"{uuid.uuid4()}.srt")

    if ASSEMBLY_AI_API_KEY is not None and ASSEMBLY_AI_API_KEY != "":
        print(colored("[+] Creating subtitles using AssemblyAI", "blue"))
        subtitles = __generate_subtitles_assemblyai(audio_path, voice)
    else:
        print(colored("[+] Creating subtitles locally with audio-aware timing", "blue"))
        subtitles = __generate_subtitles_locally(audio_path, sentences, voice, sentence_durations)

    with open(subtitles_path, "w", encoding="utf-8") as file:
        file.write(subtitles)

    equalize_subtitles(subtitles_path)

    print(colored("[+] Subtitles generated.", "green"))

    return subtitles_path


def _ffmpeg_images_to_video(image_paths: List[str], duration_per_image: float, target_w: int, target_h: int, output_path: str, durations: Optional[List[float]] = None) -> bool:
    if not image_paths:
        return False

    inputs = []
    for p in image_paths:
        if os.path.exists(p):
            inputs.append(p)

    if not inputs:
        return False

    filter_parts = []
    for i, _ in enumerate(inputs):
        scale_filter = (
            f"[{i}:v]scale=w={target_w}:h={target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},setsar=1,setpts=PTS-STARTPTS,format=yuv420p[v{i}];"
        )
        filter_parts.append(scale_filter)

    loop_input = "".join([f"[v{i}]" for i in range(len(inputs))])
    concat_filter = f"{loop_input}concat=n={len(inputs)}:v=1:a=0[vout];"
    filter_parts.append(concat_filter)

    filter_complex = "".join(filter_parts)

    cmd = ["ffmpeg", "-y", "-hwaccel", "auto"]
    for i, p in enumerate(inputs):
        dur = durations[i] if durations and i < len(durations) else duration_per_image
        cmd.extend(["-loop", "1", "-t", str(dur), "-i", p])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-an",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(colored(f"[-] ffmpeg images concat failed: {result.stderr[-500:]}", "yellow"))
            return False
        return os.path.exists(output_path)
    except Exception as e:
        print(colored(f"[-] ffmpeg images concat exception: {e}", "yellow"))
        return False


def _ffmpeg_prepend_images(image_paths: List[str], duration_per_image: float, video_path: str, target_w: int, target_h: int, output_path: str) -> bool:
    if not image_paths or not os.path.exists(video_path):
        return False

    inputs = [p for p in image_paths if os.path.exists(p)]
    if not inputs:
        return False

    n_images = len(inputs)
    vid_idx = n_images

    filter_parts = []
    for i, _ in enumerate(inputs):
        scale_filter = (
            f"[{i}:v]scale=w={target_w}:h={target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},setsar=1,setpts=PTS-STARTPTS,format=yuv420p[v{i}];"
        )
        filter_parts.append(scale_filter)

    video_scale = (
        f"[{vid_idx}:v]scale=w={target_w}:h={target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},setsar=1,setpts=PTS-STARTPTS,format=yuv420p[v{vid_idx}];"
    )
    filter_parts.append(video_scale)

    all_inputs = "".join([f"[v{i}]" for i in range(n_images + 1)])
    concat_filter = f"{all_inputs}concat=n={n_images + 1}:v=1:a=0[vout]"
    filter_parts.append(concat_filter)

    filter_complex = "".join(filter_parts)

    cmd = ["ffmpeg", "-y", "-hwaccel", "auto"]
    for p in inputs:
        cmd.extend(["-loop", "1", "-t", str(duration_per_image), "-i", p])
    cmd.extend(["-i", video_path])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-an",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(colored(f"[-] ffmpeg prepend images failed: {result.stderr[-500:]}", "yellow"))
            return False
        return os.path.exists(output_path)
    except Exception as e:
        print(colored(f"[-] ffmpeg prepend images exception: {e}", "yellow"))
        return False


def get_aspect_ratio_dimensions(aspect_ratio: str) -> tuple:
    aspect_map = {
        "9:16": (1080, 1920),
        "16:9": (1920, 1080),
        "1:1": (1080, 1080),
        "4:5": (1080, 1350),
        "21:9": (2520, 1080),
    }
    return aspect_map.get(aspect_ratio, (1080, 1920))


def get_aspect_ratio_value(aspect_ratio: str) -> float:
    w, h = get_aspect_ratio_dimensions(aspect_ratio)
    return w / h


def _ffprobe_duration(path: str) -> float:
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        print(colored(f"[-] ffprobe failed: {e}", "yellow"))
    return 0.0


def _ffmpeg_concat_clips(clip_paths: List[str], target_duration: float, target_w: int, target_h: int, output_path: str) -> bool:
    if not clip_paths:
        return False

    inputs = []
    for p in clip_paths:
        if os.path.exists(p):
            inputs.append(p)

    if not inputs:
        return False

    filter_parts = []
    for i, _ in enumerate(inputs):
        scale_filter = (
            f"[{i}:v]scale=w={target_w}:h={target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},setsar=1,setpts=PTS-STARTPTS,format=yuv420p[v{i}]"
        )
        filter_parts.append(scale_filter)

    loop_input = "".join([f"[v{i}]" for i in range(len(inputs))])
    concat_filter = f"{loop_input}concat=n={len(inputs)}:v=1:a=0[vv]"
    filter_parts.append(concat_filter)

    total_input_duration = sum(_ffprobe_duration(p) for p in inputs)
    if total_input_duration <= 0:
        total_input_duration = len(inputs) * 5.0
    loops = max(1, int(target_duration / total_input_duration) + 1)
    if loops > 1:
        loop_filter = f"[vv]loop=loop={loops}:size=1:start=0,trim=duration={target_duration},setpts=PTS-STARTPTS[vfinal]"
    else:
        loop_filter = f"[vv]trim=duration={target_duration},setpts=PTS-STARTPTS[vfinal]"
    filter_parts.append(loop_filter)

    filter_complex = ";".join(filter_parts)

    print(colored(f"[+] ffmpeg filter_complex: {filter_complex}", "cyan"))

    cmd = ["ffmpeg", "-y"]
    for p in inputs:
        cmd.extend(["-i", p])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vfinal]",
        "-an",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(colored(f"[-] ffmpeg concat failed: {result.stderr[-500:]}", "yellow"))
            return False
        return os.path.exists(output_path)
    except Exception as e:
        print(colored(f"[-] ffmpeg concat exception: {e}", "yellow"))
        return False


def combine_videos(video_paths: List[str], max_duration: float, max_clip_duration: int, threads: int, aspect_ratio: str = "9:16", image_paths: Optional[List[str]] = None, image_duration: float = 5.0, image_durations: Optional[List[float]] = None) -> str:
    video_id = uuid.uuid4()
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "temp"))
    os.makedirs(temp_dir, exist_ok=True)
    combined_video_path = os.path.join(temp_dir, f"{video_id}-combined.mp4")

    valid_paths = [p for p in video_paths if p and os.path.exists(p)]
    if not valid_paths:
        print(colored("[-] No video paths to combine.", "red"))
        return None

    target_w, target_h = get_aspect_ratio_dimensions(aspect_ratio)
    target_ratio = target_w / target_h

    # Build image video segment if images provided
    image_video_path = None
    if image_paths:
        valid_images = [(p, image_durations[i] if image_durations and i < len(image_durations) else float(image_duration))
                        for i, p in enumerate(image_paths) if p and os.path.exists(p)]
        if valid_images:
            image_video_path = os.path.join(temp_dir, f"{uuid4()}-images.mp4")
            success = _ffmpeg_images_to_video(
                [p for p, _ in valid_images],
                duration_per_image=float(image_duration),
                target_w=target_w,
                target_h=target_h,
                output_path=image_video_path,
                durations=[d for _, d in valid_images],
            )
            if success:
                print(colored(f"[+] Created image video segment from {len(valid_images)} images", "green"))
                valid_paths = [image_video_path] + valid_paths
            else:
                print(colored("[-] Failed to create image video, skipping images", "yellow"))

    print(colored(f"[+] Combining {len(valid_paths)} videos at {aspect_ratio} ({target_w}x{target_h})...", "blue"))

    use_ffmpeg = _ffmpeg_concat_clips(
        valid_paths,
        target_duration=float(max_duration),
        target_w=target_w,
        target_h=target_h,
        output_path=combined_video_path,
    )

    if use_ffmpeg:
        print(colored("[+] Videos combined (fast ffmpeg path).", "green"))
        return combined_video_path

    print(colored("[*] Falling back to MoviePy-based combination.", "yellow"))

    req_dur = float(max_duration) / max(1, len(valid_paths))

    clips = []
    tot_dur = 0
    while tot_dur < max_duration:
        for video_path in valid_paths:
            try:
                clip = VideoFileClip(video_path)
            except Exception as e:
                print(colored(f"[-] Could not open {video_path}: {e}", "yellow"))
                continue

            if clip is None:
                continue

            clip = clip.without_audio()
            if (max_duration - tot_dur) < clip.duration:
                clip = clip.subclip(0, (max_duration - tot_dur))
            elif req_dur < clip.duration:
                clip = clip.subclip(0, req_dur)

            source_ratio = round(clip.w / clip.h, 4) if clip.h else 1.0
            if source_ratio < target_ratio:
                clip = crop(
                    clip,
                    width=clip.w,
                    height=round(clip.w / target_ratio),
                    x_center=clip.w / 2,
                    y_center=clip.h / 2,
                )
            else:
                clip = crop(
                    clip,
                    width=round(target_ratio * clip.h),
                    height=clip.h,
                    x_center=clip.w / 2,
                    y_center=clip.h / 2,
                )
            clip = clip.resize((target_w, target_h))

            if clip.duration > max_clip_duration:
                clip = clip.subclip(0, max_clip_duration)

            clips.append(clip)
            tot_dur += clip.duration

    if not clips:
        print(colored("[-] No clips could be processed.", "red"))
        return None

    final_clip = concatenate_videoclips(clips)
    final_clip = final_clip.set_fps(30)
    final_clip.write_videofile(combined_video_path, threads=max(1, threads))
    final_clip.close()
    for c in clips:
        try:
            c.close()
        except Exception:
            pass

    print(colored("[+] Final video created (MoviePy).", "green"))
    return combined_video_path


def _resolve_subtitle_template(template_value: str):
    try:
        templates = subtitleTemplates.get("options", [])
        for t in templates:
            if t.get("value") == template_value:
                return t
    except Exception:
        pass
    return None


def _get_font_family(font_path: str) -> str:
    try:
        result = subprocess.run(
            ["fc-scan", "--format", "%{family}", font_path],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split(",")[0]
    except Exception:
        pass
    return os.path.splitext(os.path.basename(font_path))[0]


def _ffmpeg_render_with_subtitles(
    video_path: str,
    audio_path: str,
    subtitles_path: str,
    output_path: str,
    font_path: str,
    fontsize: int,
    color: str,
    stroke_color: str,
    stroke_width: int,
    position: str,
    target_w: int,
    target_h: int,
) -> bool:
    def hex_to_ass(hex_color: str) -> str:
        h = hex_color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}"

    primary = hex_to_ass(color)
    outline = hex_to_ass(stroke_color)

    pos_map = {
        "center,bottom": 2,
        "center,center": 5,
        "center,top": 8,
    }
    alignment = pos_map.get(position, 2)

    font_family = _get_font_family(font_path)
    font_dir = os.path.dirname(os.path.abspath(font_path))

    # ASS PlayRes defaults to 384x288 for SRT. FontSize is in units at PlayResY=288.
    # To render a font at "fontsize" pixels tall at target_h video height:
    #   ass_fontsize = fontsize * 288 / target_h
    ass_playres_y = 288
    fontsize_ass = max(12, round(fontsize * ass_playres_y / target_h))
    stroke_width_ass = max(0, round(stroke_width * ass_playres_y / target_h))

    ass_style = (
        f"FontName={font_family},"
        f"FontSize={fontsize_ass},"
        f"PrimaryColour={primary},"
        f"OutlineColour={outline},"
        f"Outline={stroke_width_ass},"
        f"BorderStyle=1,"
        f"Alignment={alignment}"
    )

    # ffmpeg filter syntax uses , to separate filters and : to separate options.
    # Escape both inside force_style so libass receives them intact.
    escaped_style = ass_style.replace(",", "\\,").replace(":", "\\:")
    safe_subs = subtitles_path.replace(":", "\\:")
    safe_fontdir = font_dir.replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y", "-hwaccel", "auto",
        "-i", video_path,
        "-i", audio_path,
        "-vf", f"subtitles={safe_subs}:fontsdir={safe_fontdir}:original_size={target_w}x{target_h}:force_style={escaped_style}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(colored(f"[-] ffmpeg subtitle render failed: {result.stderr[-500:]}", "yellow"))
            return False
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(colored("[+] Video rendered with subtitles (fast ffmpeg path).", "green"))
            return True
        return False
    except Exception as e:
        print(colored(f"[-] ffmpeg subtitle render exception: {e}", "yellow"))
        return False


def generate_video(
    combined_video_path: str,
    tts_path: str,
    subtitles_path: str,
    threads: int,
    subtitles_position: str,
    subtitle_template: str = "classic",
    aspect_ratio: str = "9:16",
) -> str:
    print(colored("[+] Starting video generation...", "green"))

    globalSettings = get_settings()
    target_w, target_h = get_aspect_ratio_dimensions(aspect_ratio)
    print(colored(f"[+] Aspect ratio: {aspect_ratio} -> {target_w}x{target_h}", "blue"))

    template = _resolve_subtitle_template(subtitle_template)
    if template:
        font_filename = globalSettings["fontOptions"].get("current", "bold_font.ttf")
        font_path = os.path.join("static", "assets", "fonts", font_filename)
        color = template.get("color", globalSettings["fontSettings"]["color"])
        stroke_color = template.get("stroke_color", globalSettings["fontSettings"]["stroke_color"])
        stroke_width = template.get("stroke_width", globalSettings["fontSettings"]["stroke_width"])
        fontsize = template.get("fontsize", globalSettings["fontSettings"]["fontsize"])
        template_position = template.get("position", "center,bottom")
    else:
        font_path = globalSettings["fontSettings"]["font"]
        color = globalSettings["fontSettings"]["color"]
        stroke_color = globalSettings["fontSettings"]["stroke_color"]
        stroke_width = globalSettings["fontSettings"]["stroke_width"]
        fontsize = globalSettings["fontSettings"]["fontsize"]
        template_position = globalSettings["fontSettings"]["subtitles_position"]

    if not os.path.isabs(font_path):
        font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), font_path))
    if not os.path.exists(font_path):
        font_path = globalSettings["fontSettings"]["font"]
        if not os.path.isabs(font_path):
            font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), font_path))

    base_h = 1920
    scale_factor = target_h / base_h if base_h else 1.0
    fontsize = max(20, int(fontsize * scale_factor))
    stroke_width = max(1, int(stroke_width * scale_factor))

    horizontal_subtitles_position, vertical_subtitles_position = template_position.split(",")
    if subtitles_position and subtitles_position.strip():
        try:
            horizontal_subtitles_position, vertical_subtitles_position = subtitles_position.split(",")
        except Exception:
            pass

    generated_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "generated_videos"))

    # --- TRY FFMPEG FAST PATH FIRST ---
    fast_video_name = os.path.join(generated_dir, f"{uuid4()}-final.mp4")
    print(colored("[+] Trying ffmpeg subtitle render (fast path)...", "blue"))
    if _ffmpeg_render_with_subtitles(
        combined_video_path,
        tts_path,
        subtitles_path,
        fast_video_name,
        font_path,
        fontsize,
        color,
        stroke_color,
        stroke_width,
        f"{horizontal_subtitles_position},{vertical_subtitles_position}",
        target_w,
        target_h,
    ):
        return fast_video_name

    print(colored("[*] Falling back to MoviePy subtitle render.", "yellow"))

    # --- MOVIEPY FALLBACK ---
    def generator(txt):
        return TextClip(
            txt,
            font=font_path,
            fontsize=fontsize,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method="label",
        )

    print(colored(f"[+] Subtitles Path: {subtitles_path}", "green"))
    subtitles = SubtitlesClip(subtitles_path, generator)

    try:
        base_video = VideoFileClip(combined_video_path)
        if base_video.w != target_w or base_video.h != target_h:
            base_video = base_video.resize((target_w, target_h))
    except Exception as e:
        print(colored(f"[-] Error loading combined video: {e}", "red"))
        return None

    audio = AudioFileClip(tts_path)
    target_duration = float(audio.duration)

    if base_video.duration < target_duration:
        try:
            base_video = base_video.loop(duration=target_duration)
        except Exception:
            try:
                base_video = base_video.set_duration(target_duration)
            except Exception:
                pass
    elif base_video.duration > target_duration:
        base_video = base_video.subclip(0, target_duration)

    subtitles = subtitles.set_duration(target_duration)

    result = CompositeVideoClip([
        base_video,
        subtitles.set_pos((horizontal_subtitles_position, vertical_subtitles_position))
    ]).set_duration(target_duration)

    result = result.set_audio(audio)

    video_name = os.path.join(generated_dir, f"{uuid4()}-final.mp4")
    print(colored("[+] Writing video...", "green"))
    result.write_videofile(video_name, threads=max(1, threads), codec="libx264", preset="ultrafast", audio_codec="aac")

    try:
        base_video.close()
    except Exception:
        pass
    try:
        audio.close()
    except Exception:
        pass
    try:
        subtitles.close()
    except Exception:
        pass
    try:
        result.close()
    except Exception:
        pass

    return video_name


def ffmpeg_add_music_to_video(
    video_path: str,
    music_path: str,
    output_path: str,
    volume: float = 0.1,
) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", music_path,
        "-filter_complex",
        f"[0:a][1:a]amix=inputs=2:duration=first:volume={volume}[audio]",
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "[audio]",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(colored(f"[-] ffmpeg add music failed: {result.stderr[-500:]}", "yellow"))
            return False
        if os.path.exists(output_path):
            print(colored("[+] Music added (fast ffmpeg path, video stream copied).", "green"))
            return True
        return False
    except Exception as e:
        print(colored(f"[-] ffmpeg add music exception: {e}", "yellow"))
        return False
