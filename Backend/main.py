import os
import requests
from utils import *
from dotenv import load_dotenv

# Load environment variables
# check if .env is in the folder or look one more level up
if os.path.exists(".env"):
    load_dotenv(".env")
else:
    load_dotenv("../.env")
# Check if all required environment variables are set
# This must happen before importing video which uses API keys without checking
check_env_vars()

from gpt import *
from video import *
from search import *
from classes.Shorts import *
from uuid import uuid4
from tiktokvoice import *
from settings import *
from flask_cors import CORS
from termcolor import colored
from youtube import upload_video
from apiclient.errors import HttpError
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from moviepy.config import change_settings
from classes.instagram_downloader import InstagramDownloader

# Set environment variables
SESSION_ID = os.getenv("TIKTOK_SESSION_ID")
openai_api_key = os.getenv('OPENAI_API_KEY')
change_settings({"IMAGEMAGICK_BINARY": os.getenv("IMAGEMAGICK_BINARY")})


# Initialize Flask
app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app, expose_headers=[
    "Content-Range", "Accept-Ranges", "Content-Length",
    "Cache-Control", "Content-Type", "Content-Disposition"
])

# Constants
HOST = "0.0.0.0"
PORT = 8080
AMOUNT_OF_STOCK_VIDEOS = 5
GENERATING = False

# Create a method to create all the required folders
def create_folders():
    """Create all required folders for the application"""
    folders = [
        "static",
        "static/assets",
        "static/assets/temp",
        "static/assets/subtitles",
        "static/generated_videos",
        "static/generated_videos/instagram",
    ]
    
    for folder in folders:
        folder_path = os.path.join(os.path.dirname(__file__), folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"Created/verified folder: {folder_path}")

# Create folders
create_folders()

# Instagram video download endpoint
@app.route("/api/instagram/download", methods=["POST"])
def download_instagram_video():
    try:
        data = request.get_json()
        video_url = data.get('url')
        
        if not video_url:
            return jsonify({
                "status": "error",
                "message": "No Instagram URL provided",
            }), 400

        # Initialize downloader with output path in static/assets
        downloader = InstagramDownloader(output_path=os.path.join(os.path.dirname(__file__), "static/generated_videos/instagram"))
        
        # Download the video
        result = downloader.download_video(video_url)
        
        return jsonify({
            "status": "success",
            "message": "Video downloaded successfully",
            "data": result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


# Generation Endpoint
@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        # Set global variable
        global GENERATING
        GENERATING = True

        # Clean
        clean_dir(os.path.join(os.path.dirname(__file__), "static/assets/temp/"))
        clean_dir(os.path.join(os.path.dirname(__file__), "static/assets/subtitles/"))


        # Parse JSON
        data = request.get_json()
        paragraph_number = int(data.get('paragraphNumber', 1))  # Default to 1 if not provided
        ai_model = data.get('aiModel')  # Get the AI model selected by the user
        n_threads = data.get('threads')  # Amount of threads to use for video generation
        subtitles_position = data.get('subtitlesPosition')  # Position of the subtitles in the video

        # Get 'useMusic' from the request data and default to False if not provided
        use_music = data.get('useMusic', False)

        # Get 'automateYoutubeUpload' from the request data and default to False if not provided
        automate_youtube_upload = data.get('automateYoutubeUpload', False)
        # Print little information about the video which is to be generated
        print(colored("[Video to be generated]", "blue"))
        print(colored("   Subject: " + data["videoSubject"], "blue"))
        print(colored("   AI Model: " + ai_model, "blue"))  # Print the AI model being used
        print(colored("   Custom Prompt: " + data["customPrompt"], "blue"))  # Print the AI model being used



        if not GENERATING:
            return jsonify(
                {
                    "status": "error",
                    "message": "Video generation was cancelled.",
                    "data": [],
                }
            )
        
        voice = data["voice"]
        voice_prefix = voice[:2]


        if not voice:
            print(colored("[!] No voice was selected. Defaulting to \"en_us_001\"", "yellow"))
            voice = "en_us_001"
            voice_prefix = voice[:2]


        videoClass = Shorts(data["videoSubject"], paragraph_number, ai_model, data["customPrompt"])
        # Generate a script
        videoClass.GenerateScript()
        # Generate search terms
        videoClass.GenerateSearchTerms()

        videoClass.DownloadVideos()

        if not GENERATING:
            return jsonify(
                {
                    "status": "error",
                    "message": "Video generation was cancelled.",
                    "data": [],
                }
            )

        videoClass.GenerateVoice(voice)
        # Concatenate videos
        videoClass.CombineVideos()

        videoClass.GenerateMetadata()

        if automate_youtube_upload:
            # Start Youtube Uploader
            # Check if the CLIENT_SECRETS_FILE exists
            client_secrets_file = os.path.abspath("./client_secret.json")
            SKIP_YT_UPLOAD = False
            if not os.path.exists(client_secrets_file):
                SKIP_YT_UPLOAD = True
                print(colored("[-] Client secrets file missing. YouTube upload will be skipped.", "yellow"))
                print(colored("[-] Please download the client_secret.json from Google Cloud Platform and store this inside the /Backend directory.", "red"))

            # Only proceed with YouTube upload if the toggle is True  and client_secret.json exists.
            if not SKIP_YT_UPLOAD:
                # Choose the appropriate category ID for your videos
                video_category_id = "28"  # Science & Technology
                privacyStatus = "private"  # "public", "private", "unlisted"
                video_metadata = {
                    'video_path': os.path.abspath(f"../temp/{final_video_path}"),
                    'title': title,
                    'description': description,
                    'category': video_category_id,
                    'keywords': ",".join(keywords),
                    'privacyStatus': privacyStatus,
                }

                # Upload the video to YouTube
                try:
                    # Unpack the video_metadata dictionary into individual arguments
                    video_response = upload_video(
                        video_path=video_metadata['video_path'],
                        title=video_metadata['title'],
                        description=video_metadata['description'],
                        category=video_metadata['category'],
                        keywords=video_metadata['keywords'],
                        privacy_status=video_metadata['privacyStatus']
                    )
                    print(f"Uploaded video ID: {video_response.get('id')}")
                except HttpError as e:
                    print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")

        
        videoClass.AddMusic(use_music)
        # Let user know
        print(colored(f"[+] Video generated: {videoClass.get_final_video_path}!", "green"))
        videoClass.Stop()

        final_video_path = "/static" + videoClass.get_final_video_path.split("/static")[1]
        # Return JSON
        return jsonify(
            {
                "status": "success",
                "message": "Video generated! See MoneyPrinter/output.mp4 for result.",
                "data": final_video_path,
            }
        )
    except Exception as err:
        print(colored(f"[-] Error: {str(err)}", "red"))
        return jsonify(
            {
                "status": "error",
                "message": f"Could not retrieve stock videos: {str(err)}",
                "data": [],
            }
        )


@app.route("/api/cancel", methods=["POST"])
def cancel():
    print(colored("[!] Received cancellation request...", "yellow"))

    global GENERATING
    GENERATING = False

    return jsonify({"status": "success", "message": "Cancelled video generation."})

# Route to generate the script and return the video script
@app.route("/api/script", methods=["POST"])
def generate_script_only():
    # Set generating to true
    GENERATING = True

    clean_dir(os.path.join(os.path.dirname(__file__), "static/assets/subtitles/"))
    print(colored("[+] Received script request...", "green"))

    data = request.get_json()
    video_subject = data["videoSubject"]
    extra_prompt = data["extraPrompt"]
    ai_model = data["aiModel"]

    videoClass = Shorts(video_subject, 1, ai_model, "",extra_prompt=extra_prompt)
    script = videoClass.GenerateScript()



    search_terms = videoClass.GenerateSearchTerms()
    
    # Show the search terms 
    print(colored(f"Search terms: {', '.join(search_terms)}", "cyan"))

    return jsonify(
        {
            "status": "success",
            "message": "Script generated!",
            "data": {
                "script": script,
                "search": search_terms
            },
        }
    )

# Download the videos and split the script
@app.route("/api/search-and-download", methods=["POST"])
def search_and_download():
    # Set generating to true
    global GENERATING
    GENERATING = True 
     # Clean
    clean_dir(os.path.join(os.path.dirname(__file__), "static/assets/temp/"))
    clean_dir(os.path.join(os.path.dirname(__file__), "static/assets/subtitles/"))

    
    print(colored("[+] Received search and download request...", "green"))

    data = request.get_json()
    search_terms = data["search"]
    script = data["script"]
    ai_model = data["aiModel"]
    voice = data["voice"]
    selectedVideoUrls = data.get("selectedVideoUrls",[])

    # Extra options:
    custom_video = data.get("videoUrls",[])
    custom_voice = data.get("voiceUrl","")
    # Set the default subtitles_position to the center, bottom
    subtitles_position = data.get("subtitlesPosition", "center,bottom")
    n_threads = data.get('threads', 4)
    # Subtitle template, aspect ratio
    subtitle_template = data.get("subtitleTemplate", "classic")
    aspect_ratio = data.get("aspectRatio", "9:16")
    custom_subtitle = data.get("customSubtitle", "")

    if not voice:
        print(colored("[!] No voice was selected. Defaulting to \"en_us_001\"", "yellow"))
        voice = "en_us_001"
    # Search for a video of the given search term
    videoClass = Shorts("", 1, ai_model, '')
    videoClass.search_terms = search_terms
    videoClass.final_script = script
    videoClass.subtitles_position = subtitles_position
    videoClass.subtitle_template = subtitle_template
    videoClass.aspect_ratio = aspect_ratio
    videoClass.custom_subtitle = custom_subtitle

    videoClass.DownloadVideos(selectedVideoUrls)

    videoClass.GenerateVoice(voice)

    videoClass.CombineVideos()

    videoClass.GenerateMetadata()
    
    videoClass.Stop()



    # FInal videoClass.get_final_video_path
    print(colored(f"[X] Next FInal video: {videoClass.get_final_video_path}", "green"))
    # if final video path is None return status code 500
    if videoClass.get_final_video_path is None:
        return jsonify(
            {
                "status": "error",
                "message": "Video generation was cancelled.",
                "data": [],
            }
        ),500
    
    # /home/myuser/MoneyPrinter/Backend/static  -> need to return only  /static/**
    final_video_path = "/static" + videoClass.get_final_video_path.split("/static")[1]
    
    # We also have the TTS path and subtitles path, which should be returned as paths accessible via standard static hosting
    final_audio_path = "/static" + videoClass.get_tts_path.split("/static")[1] if videoClass.get_tts_path else None
    final_subtitles_path = "/static" + videoClass.get_subtitles_path.split("/static")[1] if videoClass.get_subtitles_path else None

    return jsonify(
        {
            "status": "success",
            "message": "Search and download complete!",
            "data": {
                "finalAudio": final_audio_path,
                "subtitles": final_subtitles_path,
                # Should remove the complete path and just leave the 
                "finalVideo": final_video_path
            }
        }
    )

# Add audio to the video
@app.route("/api/addAudio", methods=["POST"])
def addAudio():
    GENERATING = True
    data = request.get_json()
    final_video_path = data["finalVideo"]
    song_path = data.get("songPath", "")
    ai_model = data.get("aiModel", "g4f")
    music_source = data.get("musicSource", "library")
    background_music_from_video = data.get("backgroundMusicFromVideo", "")
    aspect_ratio = data.get("aspectRatio", "9:16")

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    videoClass = Shorts("", 1, ai_model, '')
    videoClass.aspect_ratio = aspect_ratio
    videoClass.final_video_path = os.path.join(backend_dir, final_video_path.lstrip("/"))

    actual_song_path = song_path
    if music_source == "video":
        if background_music_from_video:
            if background_music_from_video.startswith("http://") or background_music_from_video.startswith("https://"):
                try:
                    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "temp"))
                    os.makedirs(temp_dir, exist_ok=True)
                    local_video = save_video(background_music_from_video, directory=temp_dir)
                    if local_video and os.path.exists(local_video):
                        actual_song_path = local_video
                    else:
                        return jsonify(
                            {
                                "status": "error",
                                "message": "Could not download the source video to extract audio.",
                                "data": [],
                            }
                        ), 400
                except Exception as e:
                    return jsonify(
                        {
                            "status": "error",
                            "message": f"Error downloading source video: {str(e)}",
                            "data": [],
                        }
                    ), 500
            else:
                actual_song_path = background_music_from_video
        else:
            return jsonify(
                {
                    "status": "error",
                    "message": "No source video selected for music extraction.",
                    "data": [],
                }
            ), 400

    videoClass.AddMusic(True, actual_song_path, music_source=music_source if music_source == "video" else "library")

    videoClass.Stop()
    final_music_path = videoClass.get_final_music_video_path
    if not final_music_path:
        return jsonify(
            {
                "status": "error",
                "message": "Could not add music to the video.",
                "data": [],
            }
        ), 500
    return jsonify(
        {
            "status": "success",
            "message": "Music added to the video successfully.",
            "data": {
                "finalVideo": "static/generated_videos/" + final_music_path
            }
        }
    )


@app.route("/api/upload-music", methods=["POST"])
def upload_music():
    music_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "music"))
    os.makedirs(music_dir, exist_ok=True)

    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No file selected"}), 400

    allowed_ext = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        return jsonify({"status": "error", "message": f"Unsupported audio format: {ext}. Allowed: {', '.join(allowed_ext)}"}), 400

    filename = secure_filename(file.filename)
    file.save(os.path.join(music_dir, filename))
    print(colored(f"[+] Uploaded music: {filename}", "green"))
    return jsonify({"status": "success", "message": f"Uploaded {filename}", "data": {"filename": filename}})


@app.route("/api/download-music-url", methods=["POST"])
def download_music_url():
    music_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "music"))
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "assets", "temp"))
    os.makedirs(music_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"status": "error", "message": "No URL provided"}), 400

    try:
        import yt_dlp
        import subprocess
        import uuid
        import shutil

        print(colored(f"[X] Downloading video from: {url}", "blue"))

        download_id = str(uuid.uuid4())[:8]
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": os.path.join(temp_dir, f"{download_id}.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            title = info.get("title", "audio")

        if not os.path.exists(video_path):
            # try with mkv extension (yt-dlp merges to mkv sometimes)
            base = os.path.splitext(video_path)[0]
            for ext in [".mkv", ".webm", ".mp4"]:
                candidate = base + ext
                if os.path.exists(candidate):
                    video_path = candidate
                    break

        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()[:60]
        output_mp3 = os.path.join(music_dir, f"{safe_title}.mp3")

        print(colored(f"[X] Extracting audio to: {output_mp3}", "blue"))
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-ab", "192k", output_mp3, "-y"],
            capture_output=True, check=True
        )

        os.remove(video_path)

        final_name = os.path.basename(output_mp3)
        print(colored(f"[+] Downloaded and extracted audio: {final_name}", "green"))
        return jsonify({
            "status": "success",
            "message": f"Downloaded and extracted audio: {final_name}",
            "data": {"filename": final_name, "title": title}
        })

    except subprocess.CalledProcessError as e:
        print(colored(f"[-] FFmpeg error: {e.stderr.decode()[:200]}", "red"))
        return jsonify({"status": "error", "message": f"Audio extraction failed: {e.stderr.decode()[:200]}"}), 500
    except Exception as e:
        print(colored(f"[-] Error downloading audio: {str(e)}", "red"))
        return jsonify({"status": "error", "message": f"Download failed: {str(e)}"}), 500


# Get all available songs
@app.route("/api/getSongs", methods=["GET"])
def get_songs():
    songs = os.listdir(os.path.join(os.path.dirname(__file__), "static/assets/music"))
    return jsonify({
        "status": "success",
        "message": "Songs retrieved successfully!",
        "data": {
            "songs": songs
        }
    })

# Get all available videos
@app.route("/api/getVideos", methods=["GET"])
def get_videos():
    generated_dir = os.path.join(os.path.dirname(__file__), "static/generated_videos")
    videos = [f for f in os.listdir(generated_dir) if f.endswith(".mp4")]

    video_list = []
    for video in videos:
        metadata = None
        meta_path = os.path.join(generated_dir, video.replace(".mp4", ".json"))
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    metadata = json.load(f)
            except Exception:
                pass
        video_list.append({
            "filename": video,
            "url": f"/api/video/{video}",
            "metadata": metadata
        })

    instagram_dir = os.path.join(generated_dir, "instagram")
    instagram_videos = []
    if os.path.exists(instagram_dir):
        for f in os.listdir(instagram_dir):
            if f.endswith(".mp4"):
                metadata = None
                meta_path = os.path.join(instagram_dir, f.replace(".mp4", ".json"))
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path) as mf:
                            metadata = json.load(mf)
                    except Exception:
                        pass
                instagram_videos.append({
                    "filename": f,
                    "url": f"/api/video/instagram/{f}",
                    "metadata": metadata
                })
    return jsonify(
        {
        "status": "success",
        "message": "Videos retrieved successfully!",
        "data": {
            "videos": video_list,
            "instagram": instagram_videos
            }
        }
    )

# Get all available subtitles
@app.route("/api/getSubtitles", methods=["GET"])
def get_subtitles():
    subtitles = os.listdir(os.path.join(os.path.dirname(__file__), "static/assets/subtitles"))
    return jsonify(
        {
        "status": "success",
        "message": "Songs retrieved successfully!",
        "data": {
            "subtitles": subtitles
            }
        }
    )


#Get all available models and voices
@app.route("/api/models", methods=["GET"])
def get_models():
    engine = get_tts_engine()
    voices = get_all_voices().get(engine, get_tiktok_voices())
    result = {
        "voices": voices,
        "tts_engine": engine,
    }
    if engine == "supertonic":
        result["voiceStyles"] = get_supertonic_voices_detailed()
        result["languages"] = get_supertonic_languages()
        result["qualityPresets"] = get_supertonic_quality_presets()
    return jsonify(
        {
        "status": "success",
        "message": "Models retrieved successfully!",
        "data": result
        }
    )


@app.route("/api/assets", methods=["GET"])
def get_assets():
    assets_path = os.path.join(os.path.dirname(__file__), "static/assets/temp")
    video_assets = os.listdir(assets_path)
    videos = [video for video in video_assets if video.endswith(".mp4")]
    return jsonify(
        {
        "status": "success",
        "message": "Assets retrieved successfully!",
        "data": {
            "videos": videos
            }
        }
    )



@app.route("/api/settings", methods=["GET"])
def get_global_settings():

    global_settings = get_settings()
    return jsonify(
        {
        "status": "success",
        "message": "System settings retrieved successfully!",
        "data": global_settings
        }
    )


@app.route("/api/settings", methods=["POST"])
def update_global_settings():
    data = request.get_json()
    setting_type = data.get("type", "FONT")
    settings = data.get("settings", {})
    update_settings(settings, setting_type)
    return jsonify(
        {
        "status": "success",
        "message": "Settings updated successfully!",
        "data": get_settings()
        }
    )


@app.route("/api/tts/status", methods=["GET"])
def get_tts_health():
    status = get_tts_status()
    return jsonify(
        {
        "status": "success",
        "message": "TTS status retrieved successfully!",
        "data": status
        }
    )


@app.route("/api/tts/voices", methods=["GET"])
def get_tts_voices():
    engine = request.args.get("engine", get_tts_engine())
    voices = get_all_voices().get(engine, get_tiktok_voices())
    result = {
        "voices": voices,
        "engine": engine,
    }
    if engine == "supertonic":
        result["voiceStyles"] = get_supertonic_voices_detailed()
        result["languages"] = get_supertonic_languages()
        result["qualityPresets"] = get_supertonic_quality_presets()
    return jsonify(
        {
        "status": "success",
        "message": "Voices retrieved successfully!",
        "data": result
        }
    )


@app.route("/api/magicsync/accounts", methods=["POST"])
def magicsync_accounts():
    try:
        data = request.get_json()
        url = data.get("url", os.getenv("MAGICSYNC_BASE_URL", "http://localhost:3000"))
        api_token = data.get("apiToken", os.getenv("MAGICSYNC_API_TOKEN", ""))

        print(colored(f"[X] MagicSync accounts request", "blue"))
        print(colored(f"[X]   URL: {url}", "blue"))
        print(colored(f"[X]   API token present: {'yes' if api_token else 'no'}", "blue"))

        if not api_token:
            print(colored("[-]   MISSING: API token", "red"))
            return jsonify({"status": "error", "message": "API token is required. Provide it in the request or set MAGICSYNC_API_TOKEN in Backend/.env"}), 400

        target_url = f"{url}/api/v1/cli/info"
        print(colored(f"[X]   GETting from: {target_url}", "blue"))

        info_resp = requests.get(
            target_url,
            headers={"x-api-key": api_token},
            timeout=10
        )

        print(colored(f"[X]   Response status: {info_resp.status_code}", "blue"))
        try:
            resp_body = info_resp.json()
            print(colored(f"[X]   Response body: {json.dumps(resp_body, indent=2)[:800]}", "blue"))
        except Exception:
            print(colored(f"[X]   Response text: {info_resp.text[:500]}", "blue"))

        if info_resp.status_code != 200:
            print(colored(f"[-] MagicSync info failed: {info_resp.text[:200]}", "red"))
            return jsonify({"status": "error", "message": f"Failed to connect: {info_resp.text}"}), 502

        platforms_data = info_resp.json()
        accounts = [
            {"platform": platform.get("platform"), "accountName": acc.get("accountName"), "isActive": acc.get("isActive", True)}
            for platform in platforms_data.get("data", {}).get("platforms", [])
            for acc in platform.get("accounts", [])
        ]

        platforms_list = list(dict.fromkeys(a.get("platform") for a in accounts if a.get("isActive")))

        print(colored(f"[+] Found {len(platforms_list)} MagicSync platform(s)", "green"))
        for p in platforms_list:
            print(colored(f"      - {p}", "green"))

        return jsonify({
            "status": "success",
            "message": "Accounts retrieved successfully!",
            "data": {"accounts": accounts, "platforms": platforms_list}
        })

    except requests.exceptions.Timeout:
        print(colored(f"[-] MagicSync info request timed out", "red"))
        return jsonify({"status": "error", "message": "MagicSync API request timed out"}), 504
    except requests.exceptions.ConnectionError as e:
        print(colored(f"[-] MagicSync API connection failed: {e}", "red"))
        return jsonify({"status": "error", "message": f"Cannot connect to MagicSync at {url}. Is the server running?"}), 502
    except Exception as e:
        print(colored(f"[-] Error fetching MagicSync accounts: {str(e)}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/video/<path:filename>")
def serve_video(filename):
    video_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "generated_videos"))
    return send_from_directory(video_dir, filename)


@app.route("/api/schedule-to-magicsync", methods=["POST"])
def schedule_to_magicsync():
    try:
        data = request.get_json()
        video_filename = data.get("videoFilename")
        scheduled_at = data.get("scheduledAt")
        content = data.get("content", "")
        title = data.get("title", "")
        description = data.get("description", "")
        platforms = data.get("platforms", [])
        video_base_url = data.get("videoBaseUrl", "")

        print(colored(f"[X] Schedule-to-MagicSync request received", "blue"))
        print(colored(f"[X]   videoFilename: {video_filename}", "blue"))
        print(colored(f"[X]   scheduledAt: {scheduled_at}", "blue"))
        print(colored(f"[X]   title: {title[:60] if title else '(empty)'}", "blue"))
        print(colored(f"[X]   platforms ({len(platforms)}): {platforms}", "blue"))

        if not video_filename:
            print(colored("[-]   MISSING: videoFilename", "red"))
            return jsonify({"status": "error", "message": "videoFilename is required"}), 400
        if not platforms:
            print(colored("[-]   MISSING: platforms is empty", "red"))
            return jsonify({"status": "error", "message": "At least one platform is required"}), 400

        url = data.get("url", os.getenv("MAGICSYNC_BASE_URL", "http://localhost:3000"))
        api_token = data.get("apiToken", os.getenv("MAGICSYNC_API_TOKEN", ""))

        print(colored(f"[X]   MagicSync URL: {url}", "blue"))
        print(colored(f"[X]   API token present: {'yes' if api_token else 'no'}", "blue"))
        print(colored(f"[X]   Video base URL: {video_base_url or '(using request host)'}", "blue"))

        if not api_token:
            print(colored("[-]   MISSING: API token", "red"))
            return jsonify({"status": "error", "message": "API token is required. Provide it in the request or set MAGICSYNC_API_TOKEN in Backend/.env"}), 400

        if video_base_url:
            video_url = f"{video_base_url.rstrip('/')}/api/video/{video_filename}"
        else:
            base_url = request.host_url.rstrip("/")
            video_url = f"{base_url}/api/video/{video_filename}"
        if not content:
            content = title or description or f"New video: {video_filename}"

        payload = {
            "content": content,
            "platforms": platforms,
            "media": {"video": video_url},
        }

        if title:
            payload["title"] = title
        if description:
            payload["description"] = description
        if scheduled_at:
            payload["scheduledAt"] = scheduled_at

        print(colored(f"[X]   Payload to MagicSync:", "blue"))
        print(colored(f"       content: {content[:80]}...", "blue"))
        print(colored(f"       media.video: {video_url}", "blue"))
        print(colored(f"       platforms: {platforms}", "blue"))
        if scheduled_at:
            print(colored(f"       scheduledAt: {scheduled_at}", "blue"))

        target_url = f"{url}/api/v1/cli/post"
        print(colored(f"[X]   POSTing to: {target_url}", "blue"))

        post_resp = requests.post(
            target_url,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_token
            },
            json=payload,
            timeout=30
        )

        print(colored(f"[X]   Response status: {post_resp.status_code}", "blue"))
        try:
            resp_body = post_resp.json()
            print(colored(f"[X]   Response body: {json.dumps(resp_body, indent=2)[:500]}", "blue"))
        except Exception:
            print(colored(f"[X]   Response text: {post_resp.text[:500]}", "blue"))

        if post_resp.status_code == 200:
            print(colored(f"[+] Video scheduled successfully!", "green"))
            return jsonify({
                "status": "success",
                "message": "Video scheduled successfully!",
                "data": post_resp.json()
            })
        else:
            print(colored(f"[-] MagicSync API returned {post_resp.status_code}", "red"))
            return jsonify({
                "status": "error",
                "message": f"MagicSync API error: {post_resp.text}"
            }), 502

    except requests.exceptions.Timeout:
        print(colored(f"[-] MagicSync API request timed out after 30s", "red"))
        return jsonify({"status": "error", "message": "MagicSync API request timed out"}), 504
    except requests.exceptions.ConnectionError as e:
        print(colored(f"[-] MagicSync API connection failed: {e}", "red"))
        return jsonify({"status": "error", "message": f"Cannot connect to MagicSync at {url}. Is the server running?"}), 502
    except Exception as e:
        print(colored(f"[-] Error scheduling video: {str(e)}", "red"))
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":

    # Run Flask App
    app.run(debug=True, host=HOST, port=PORT)
