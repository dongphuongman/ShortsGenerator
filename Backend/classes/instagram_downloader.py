import yt_dlp
import os
from typing import Optional, Dict, Any
from datetime import datetime

class InstagramDownloader:
    def __init__(self, output_path: str = "downloads"):
        """
        Initialize the Instagram video downloader
        
        Args:
            output_path (str): Directory where videos will be saved
        """
        self.output_path = output_path
        self._create_output_directory()
        
        # Configure yt-dlp options
        self.ydl_opts = {
            'format': 'best',  # Download best quality
            'outtmpl': os.path.join(self.output_path, '%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
        }

    def _get_timestamped_filename(self, original_path: str) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dir_name = os.path.dirname(original_path)
        base = os.path.splitext(os.path.basename(original_path))[0]
        ext = os.path.splitext(original_path)[1]
        new_name = f"{timestamp}_{base}{ext}"
        new_path = os.path.join(dir_name, new_name)
        os.rename(original_path, new_path)
        return new_name

    def _create_output_directory(self) -> None:
        """Create the output directory if it doesn't exist"""
        os.makedirs(self.output_path, exist_ok=True)

    def download_video(self, url: str) -> Dict[str, Any]:
        """
        Download a video from Instagram
        
        Args:
            url (str): Instagram video URL
            
        Returns:
            Dict[str, Any]: Information about the downloaded video
            
        Raises:
            Exception: If download fails
        """
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                original_path = ydl.prepare_filename(info)
                final_name = self._get_timestamped_filename(original_path)

                return {
                    'title': info.get('title', ''),
                    'filename': final_name,
                    'duration': info.get('duration'),
                    'thumbnail': info.get('thumbnail'),
                    'download_time': datetime.now().isoformat(),
                    'status': 'success'
                }
                
        except Exception as e:
            error_info = {
                'status': 'error',
                'error_message': str(e),
                'url': url,
                'time': datetime.now().isoformat()
            }
            raise Exception(f"Failed to download video: {str(e)}") from e

    def update_options(self, new_options: Dict[str, Any]) -> None:
        """
        Update yt-dlp options
        
        Args:
            new_options (Dict[str, Any]): New options to update
        """
        self.ydl_opts.update(new_options)

    def set_output_template(self, template: str) -> None:
        """
        Set custom output template for downloaded files
        
        Args:
            template (str): Output template string
        """
        self.ydl_opts['outtmpl'] = os.path.join(self.output_path, template)
