"""
EnCore's SnapSave - Media Downloader Engine
Supports YouTube, YouTube Shorts, Instagram, Reels, X (Twitter), Facebook, etc.
Hybrid architecture: pytubefix for YouTube streams + yt-dlp fallback and multi-platform engine.
"""

import os
import re
import time
import uuid
import glob
import logging
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("snapsave_downloader")

# Base downloads directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(CURRENT_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Locate ffmpeg executable if available
FFMPEG_PATH = None
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    pass


class MediaExtractError(Exception):
    """Custom exception for media extraction and download failures."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent filesystem issues across OSes."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:80] if clean else "media_file"


def format_duration(seconds: Optional[int]) -> str:
    """Convert seconds into HH:MM:SS or MM:SS."""
    if seconds is None or seconds < 0:
        return "Unknown"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_size(bytes_num: Optional[int]) -> str:
    """Format bytes into KB, MB, GB."""
    if not bytes_num or bytes_num <= 0:
        return "Approx. Stream"
    if bytes_num < 1024 * 1024:
        return f"{bytes_num / 1024:.1f} KB"
    if bytes_num < 1024 * 1024 * 1024:
        return f"{bytes_num / (1024 * 1024):.1f} MB"
    return f"{bytes_num / (1024 * 1024 * 1024):.2f} GB"


def detect_platform(url: str) -> str:
    """Detect platform from URL."""
    parsed = urlparse(url.strip())
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    if "youtube.com" in domain or "youtu.be" in domain:
        if "/shorts" in path:
            return "YouTube Shorts"
        return "YouTube"
    if "instagram.com" in domain:
        if "/reel" in path:
            return "Instagram Reels"
        return "Instagram"
    if "twitter.com" in domain or "x.com" in domain:
        return "X (Twitter)"
    if "facebook.com" in domain or "fb.watch" in domain:
        return "Facebook"
    if "reddit.com" in domain:
        return "Reddit"
    if "vimeo.com" in domain:
        return "Vimeo"
    return "Web Media"


def cleanup_old_downloads(max_age_seconds: int = 600) -> int:
    """
    Remove temporary downloaded files older than max_age_seconds (default: 10 minutes).
    Returns count of deleted files.
    """
    deleted_count = 0
    now = time.time()
    for file_path in glob.glob(os.path.join(DOWNLOADS_DIR, "*")):
        if os.path.isfile(file_path):
            try:
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Could not remove stale file {file_path}: {e}")
    return deleted_count


def extract_with_pytubefix(url: str) -> Dict[str, Any]:
    """Extract YouTube information using pytubefix."""
    try:
        from pytubefix import YouTube
        yt = YouTube(url)

        title = yt.title or "YouTube Video"
        thumbnail = yt.thumbnail_url or ""
        duration = yt.length or 0
        uploader = yt.author or "Unknown Creator"

        formats_list: List[Dict[str, Any]] = []
        seen_res = set()

        # 1. Progressive streams (Video + Audio combined in MP4 - fastest & guaranteed sync)
        for s in yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc():
            res = s.resolution or f"{s.itag}p"
            if res not in seen_res:
                seen_res.add(res)
                formats_list.append({
                    "format_id": f"pt_itag_{s.itag}",
                    "quality_label": f"{res} (Direct MP4)",
                    "ext": "mp4",
                    "filesize_approx": s.filesize,
                    "filesize_human": format_size(s.filesize),
                    "is_audio_only": False,
                    "has_audio": True,
                    "format_note": "Fast Download • Audio Included"
                })

        # 2. Adaptive video streams (all resolutions: 2160p, 1440p, 1080p, 720p, 480p, 360p, 240p)
        for s in yt.streams.filter(only_video=True).order_by("resolution").desc():
            res = s.resolution
            if res and res not in seen_res:
                seen_res.add(res)
                formats_list.append({
                    "format_id": f"pt_itag_{s.itag}",
                    "quality_label": f"{res} (High Quality)",
                    "ext": s.subtype or "mp4",
                    "filesize_approx": s.filesize,
                    "filesize_human": format_size(s.filesize),
                    "is_audio_only": False,
                    "has_audio": False,
                    "format_note": "Video Stream"
                })

        # 3. Audio only streams (MP3/M4A)
        audio_streams = yt.streams.filter(only_audio=True).order_by("abr").desc()
        if audio_streams:
            best_audio = audio_streams.first()
            formats_list.append({
                "format_id": f"pt_audio_{best_audio.itag}_mp3",
                "quality_label": f"Audio MP3 ({best_audio.abr or '128kbps'})",
                "ext": "mp3",
                "filesize_approx": best_audio.filesize,
                "filesize_human": format_size(best_audio.filesize),
                "is_audio_only": True,
                "has_audio": True,
                "format_note": "High Quality Audio"
            })
            formats_list.append({
                "format_id": f"pt_audio_{best_audio.itag}_m4a",
                "quality_label": f"Audio M4A ({best_audio.abr or 'Original'})",
                "ext": "m4a",
                "filesize_approx": best_audio.filesize,
                "filesize_human": format_size(best_audio.filesize),
                "is_audio_only": True,
                "has_audio": True,
                "format_note": "Original AAC Stream"
            })

        if not formats_list:
            raise MediaExtractError("No compatible video or audio streams found via pytubefix.")

        return {
            "title": title,
            "thumbnail": thumbnail,
            "duration": duration,
            "duration_formatted": format_duration(duration),
            "uploader": uploader,
            "platform": detect_platform(url),
            "engine": "pytubefix",
            "formats": formats_list
        }
    except Exception as e:
        logger.warning(f"pytubefix extraction failed: {e}. Falling back to yt-dlp...")
        raise e


def extract_with_ytdlp(url: str) -> Dict[str, Any]:
    """Extract information using yt-dlp (supports Instagram, X, FB, YouTube fallback)."""
    import yt_dlp

    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "simulate": True,
    }
    if FFMPEG_PATH:
        ydl_opts["ffmpeg_location"] = FFMPEG_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Private video" in msg:
            raise MediaExtractError("This video is private or inaccessible.", status_code=403)
        if "Sign in" in msg or "Age-restricted" in msg:
            raise MediaExtractError("This video is age-restricted or requires login.", status_code=403)
        if "This video is not available" in msg:
            raise MediaExtractError("Video is unavailable or has been removed.", status_code=404)
        if "Unsupported URL" in msg:
            raise MediaExtractError("Unsupported URL or invalid link format.", status_code=400)
        raise MediaExtractError(f"Could not retrieve media details: {msg[:160]}", status_code=400)
    except Exception as e:
        raise MediaExtractError(f"Failed to extract media information: {str(e)[:160]}", status_code=500)

    if not info:
        raise MediaExtractError("No media information could be extracted for this link.")

    title = info.get("title") or info.get("description", "")[:60] or "Media Download"
    thumbnail = info.get("thumbnail") or ""
    duration = int(info.get("duration") or 0)
    uploader = info.get("uploader") or info.get("channel") or info.get("extractor") or "Unknown"

    formats_list: List[Dict[str, Any]] = []
    seen_heights = set()

    raw_formats = info.get("formats", [])
    # If no formats array (e.g. direct Instagram video), use direct url
    if not raw_formats and info.get("url"):
        ext = info.get("ext", "mp4")
        formats_list.append({
            "format_id": "direct_url",
            "quality_label": "Standard Quality (MP4)",
            "ext": ext,
            "filesize_approx": info.get("filesize") or 0,
            "filesize_human": format_size(info.get("filesize")),
            "is_audio_only": False,
            "has_audio": True,
            "format_note": "Direct Media Stream"
        })
    else:
        # Sort video formats by height descending
        for f in sorted(raw_formats, key=lambda x: (x.get("height") or 0, x.get("tbr") or 0), reverse=True):
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            ext = f.get("ext") or "mp4"

            # Skip storyboard and audio-only in video pass
            if vcodec == "none" or "mhtml" in ext:
                continue

            height = f.get("height")
            fmt_id = str(f.get("format_id"))
            size = f.get("filesize") or f.get("filesize_approx") or 0

            # Normalize resolution label
            res_label = f"{height}p" if height else (f.get("format_note") or "Standard")
            if res_label not in seen_heights and (height or not seen_heights):
                if height:
                    seen_heights.add(res_label)
                formats_list.append({
                    "format_id": f"ytdlp_{fmt_id}",
                    "quality_label": f"{res_label} ({ext.upper()})",
                    "ext": ext if ext in ["mp4", "webm"] else "mp4",
                    "filesize_approx": size,
                    "filesize_human": format_size(size),
                    "is_audio_only": False,
                    "has_audio": acodec != "none",
                    "format_note": "Video Stream"
                })

        # Add generic best video option if needed
        if not formats_list:
            formats_list.append({
                "format_id": "ytdlp_best",
                "quality_label": "Best Available (MP4)",
                "ext": "mp4",
                "filesize_approx": 0,
                "filesize_human": "Auto Size",
                "is_audio_only": False,
                "has_audio": True,
                "format_note": "Best Quality Video"
            })

        # Add Audio MP3 extract option
        formats_list.append({
            "format_id": "ytdlp_bestaudio_mp3",
            "quality_label": "Audio MP3 (Best Audio)",
            "ext": "mp3",
            "filesize_approx": 0,
            "filesize_human": "Audio Stream",
            "is_audio_only": True,
            "has_audio": True,
            "format_note": "Extracted Audio Track"
        })

    return {
        "title": title,
        "thumbnail": thumbnail,
        "duration": duration,
        "duration_formatted": format_duration(duration),
        "uploader": uploader,
        "platform": detect_platform(url),
        "engine": "yt-dlp",
        "formats": formats_list
    }


def get_media_info(url: str) -> Dict[str, Any]:
    """
    Main info route:
    Detects platform, routes to pytubefix for YouTube, or yt-dlp for other platforms.
    Gracefully falls back to yt-dlp if pytubefix encounters issues.
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise MediaExtractError("Please provide a valid URL starting with http:// or https://")

    platform = detect_platform(url)

    if platform in ["YouTube", "YouTube Shorts"]:
        try:
            return extract_with_pytubefix(url)
        except Exception:
            logger.info("Falling back to yt-dlp for YouTube URL...")
            return extract_with_ytdlp(url)
    else:
        return extract_with_ytdlp(url)


def download_with_pytubefix(url: str, format_id: str, ext: str) -> Tuple[str, str, str]:
    """Download using pytubefix engine."""
    from pytubefix import YouTube

    yt = YouTube(url)
    title_clean = sanitize_filename(yt.title or "SnapSave_Media")
    unique_id = uuid.uuid4().hex[:8]

    # Handle audio
    if format_id.startswith("pt_audio_") or ext == "mp3":
        parts = format_id.split("_")
        itag = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
        stream = yt.streams.get_by_itag(itag) if itag else yt.streams.filter(only_audio=True).first()
        if not stream:
            raise MediaExtractError("Audio stream not available for download.")

        target_ext = "mp3" if ext == "mp3" else "m4a"
        filename = f"{title_clean}_{unique_id}.{target_ext}"
        target_path = os.path.join(DOWNLOADS_DIR, filename)

        out_file = stream.download(output_path=DOWNLOADS_DIR, filename=f"temp_{unique_id}.{stream.subtype}")
        
        # Convert to mp3 if requested and ffmpeg is present
        if target_ext == "mp3" and FFMPEG_PATH:
            cmd = [FFMPEG_PATH, "-y", "-i", out_file, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", target_path]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if os.path.exists(out_file):
                    os.remove(out_file)
            except Exception:
                if os.path.exists(target_path):
                    os.remove(target_path)
                os.rename(out_file, target_path)
        else:
            if os.path.exists(target_path):
                os.remove(target_path)
            os.rename(out_file, target_path)

        content_type = "audio/mpeg" if target_ext == "mp3" else "audio/mp4"
        return target_path, f"{title_clean}.{target_ext}", content_type

    # Handle video
    if format_id.startswith("pt_itag_"):
        itag = int(format_id.replace("pt_itag_", ""))
        stream = yt.streams.get_by_itag(itag)
        if not stream:
            stream = yt.streams.filter(file_extension="mp4").first()
        if not stream:
            raise MediaExtractError("Selected video stream not found.")

        filename = f"{title_clean}_{stream.resolution or 'video'}_{unique_id}.mp4"
        out_file = stream.download(output_path=DOWNLOADS_DIR, filename=filename)
        return out_file, f"{title_clean}_{stream.resolution or 'video'}.mp4", "video/mp4"

    # Default fallback
    stream = yt.streams.get_highest_resolution()
    if not stream:
        raise MediaExtractError("No stream available for download.")
    filename = f"{title_clean}_{unique_id}.mp4"
    out_file = stream.download(output_path=DOWNLOADS_DIR, filename=filename)
    return out_file, f"{title_clean}.mp4", "video/mp4"


def download_with_ytdlp(url: str, format_id: str, ext: str) -> Tuple[str, str, str]:
    """Download using yt-dlp engine."""
    import yt_dlp

    unique_id = uuid.uuid4().hex[:8]
    output_template = os.path.join(DOWNLOADS_DIR, f"%(title).50s_{unique_id}.%(ext)s")

    ydl_opts: Dict[str, Any] = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if FFMPEG_PATH:
        ydl_opts["ffmpeg_location"] = FFMPEG_PATH

    is_audio = ext == "mp3" or "audio" in format_id

    if is_audio:
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }] if FFMPEG_PATH else [],
        })
    elif format_id.startswith("ytdlp_") and format_id != "ytdlp_best":
        fmt_spec = format_id.replace("ytdlp_", "")
        ydl_opts["format"] = f"{fmt_spec}+bestaudio/best" if "+bestaudio" not in fmt_spec else fmt_spec
    else:
        ydl_opts["format"] = "best[ext=mp4]/best"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise MediaExtractError("yt-dlp could not complete the download.")

            # Search for downloaded file matching unique_id
            pattern = os.path.join(DOWNLOADS_DIR, f"*{unique_id}*")
            matches = glob.glob(pattern)
            if not matches:
                raise MediaExtractError("Downloaded file could not be located on disk.")

            file_path = matches[0]
            base_ext = os.path.splitext(file_path)[1].lstrip(".") or ext
            clean_title = sanitize_filename(info.get("title") or "SnapSave_Media")
            display_name = f"{clean_title}.{base_ext}"

            content_type = "audio/mpeg" if base_ext == "mp3" else "video/mp4"
            return file_path, display_name, content_type
    except Exception as e:
        logger.error(f"yt-dlp download failed: {e}")
        raise MediaExtractError(f"Download failed: {str(e)[:160]}")


def download_media(url: str, format_id: str, ext: str = "mp4") -> Tuple[str, str, str]:
    """
    Main download dispatcher:
    Picks pytubefix or yt-dlp based on format_id prefix.
    """
    cleanup_old_downloads(max_age_seconds=600)

    if format_id.startswith("pt_"):
        try:
            return download_with_pytubefix(url, format_id, ext)
        except Exception as e:
            logger.warning(f"pytubefix download failed ({e}), falling back to yt-dlp...")
            return download_with_ytdlp(url, "ytdlp_best", ext)
    else:
        return download_with_ytdlp(url, format_id, ext)
