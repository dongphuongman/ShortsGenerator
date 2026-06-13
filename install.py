#!/usr/bin/env python3
"""
ShortsGenerator Installation Script

Installs all dependencies needed for the ShortsGenerator project:
- System dependencies (ffmpeg, ImageMagick, espeak-ng)
- Python packages from requirements.txt
- KittenTTS for local TTS
"""

import os
import sys
import subprocess
import platform


def run_command(cmd, description, check=True, shell=False):
    """Run a shell command and print status."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    
    if shell:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    if check and result.returncode != 0:
        print(f"❌ Failed: {description}")
        return False
    else:
        print(f"✅ Success: {description}")
        return True


def install_system_deps():
    """Install system-level dependencies based on OS."""
    system = platform.system()
    
    if system == "Linux":
        # Check if running in Docker or on host
        if os.path.exists("/.dockerenv"):
            print("Running in Docker container")
            # In Docker, most deps should already be installed
            return True
            
        # Ubuntu/Debian
        if os.path.exists("/etc/debian_version"):
            print("Detected Debian-based Linux")
            deps = [
                "ffmpeg",
                "imagemagick",
                "espeak-ng",
                "libsox-fmt-mp3",
                "libcairo2-dev",
                "libgirepository1.0-dev",
                "gir1.2-gtk-3.0",
                "pkg-config"
            ]
            cmd = f"sudo apt-get update && sudo apt-get install -y {' '.join(deps)}"
            return run_command(cmd, "Installing system dependencies (Linux)", shell=True)
        
    elif system == "Darwin":  # macOS
        print("Detected macOS")
        deps = ["ffmpeg", "imagemagick", "espeak"]
        cmd = f"brew install {' '.join(deps)}"
        return run_command(cmd, "Installing system dependencies (macOS)", shell=True)
    
    elif system == "Windows":
        print("Windows detected. Please install manually:")
        print("  - ffmpeg: https://ffmpeg.org/download.html")
        print("  - ImageMagick: https://imagemagick.org/script/download.php")
        print("  - espeak-ng: https://github.com/espeak-ng/espeak-ng/releases")
        return True
    
    return True


def install_python_deps():
    """Install Python dependencies."""
    # Upgrade pip first
    run_command(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
        "Upgrading pip"
    )
    
    # Install requirements.txt
    requirements_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "requirements.txt"
    )
    
    if os.path.exists(requirements_path):
        run_command(
            [sys.executable, "-m", "pip", "install", "-r", requirements_path],
            "Installing Python requirements from requirements.txt"
        )
    else:
        print(f"⚠️ requirements.txt not found at {requirements_path}")
    
    # Install KittenTTS directly from the latest wheel
    # The requirements.txt has a specific version, but let's try the latest
    print("\nInstalling KittenTTS...")
    run_command(
        [sys.executable, "-m", "pip", "install", 
         "https://github.com/KittenML/KittenTTS/releases/download/0.8.1/kittentts-0.8.1-py3-none-any.whl"],
        "Installing KittenTTS v0.8.1"
    )


def verify_installation():
    """Verify that key dependencies are installed."""
    print(f"\n{'='*60}")
    print("Verifying installation...")
    print(f"{'='*60}")
    
    # Check Python packages
    packages_to_check = [
        ("flask", "Flask"),
        ("moviepy", "MoviePy"),
        ("g4f", "g4f"),
        ("kittentts", "KittenTTS"),
        ("PIL", "Pillow"),
        ("termcolor", "termcolor"),
        ("soundfile", "soundfile"),
    ]
    
    print("\nPython packages:")
    for module_name, display_name in packages_to_check:
        try:
            __import__(module_name)
            print(f"  ✅ {display_name}")
        except ImportError:
            print(f"  ❌ {display_name} - NOT INSTALLED")
    
    # Check system commands
    commands_to_check = ["ffmpeg", "convert", "espeak"]
    print("\nSystem commands:")
    for cmd in commands_to_check:
        result = subprocess.run(
            f"which {cmd}" if platform.system() != "Windows" else f"where {cmd}",
            shell=True,
            capture_output=True
        )
        if result.returncode == 0:
            print(f"  ✅ {cmd}")
        else:
            print(f"  ⚠️ {cmd} - not found in PATH (may need manual installation)")
    
    # Check if KittenTTS works
    print("\nTesting KittenTTS...")
    try:
        from kittentts import KittenTTS
        model = KittenTTS("KittenML/kitten-tts-nano-0.8-int8")
        print(f"  ✅ KittenTTS loaded successfully!")
        print(f"     Available voices: {model.available_voices}")
    except Exception as e:
        print(f"  ❌ KittenTTS test failed: {e}")
        print("  This may be due to missing system dependencies or network issues.")


def create_env_file():
    """Create .env.example if it doesn't exist."""
    env_example = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.example")
    if not os.path.exists(env_example):
        env_content = """# API Keys
PEXELS_API_KEY=your_pexels_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
TIKTOK_SESSION_ID=your_tiktok_session_id_here

# Optional
ASSEMBLY_AI_API_KEY=your_assemblyai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# ImageMagick path (Linux typically)
IMAGEMAGICK_BINARY=/usr/bin/convert
"""
        with open(env_example, "w") as f:
            f.write(env_content)
        print(f"\n✅ Created .env.example")
    else:
        print(f"\n⚠️ .env.example already exists")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              ShortsGenerator Installation Script              ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or later is required")
        sys.exit(1)
    
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.system()}")
    
    # Install system dependencies
    if not install_system_deps():
        print("\n⚠️ System dependency installation had issues, continuing...")
    
    # Install Python dependencies
    install_python_deps()
    
    # Verify installation
    verify_installation()
    
    # Create .env.example
    create_env_file()
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    Installation Complete!                     ║
╚═══════════════════════════════════════════════════════════════╝

Next steps:
1. Copy .env.example to .env and add your API keys
2. Run: cd Backend && python main.py
3. Open http://localhost:8080 to verify the API is working

For help, see: https://github.com/leamsigc/ShortsGenerator
""")


if __name__ == "__main__":
    main()
