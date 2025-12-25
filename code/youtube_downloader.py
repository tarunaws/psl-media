"""YouTube downloader utility (importable + CLI).

This module provides a safe `download_youtube` function that can be imported
and used by other parts of the project. It also includes a small CLI so you
can run it manually when needed. The script will NOT run on import.

Dependencies:
  pip install pytube==12.1.0

Usage (CLI):
  python code/youtube_downloader.py --url "https://youtube.com/watch?v=..." --output . --filename myvideo.mp4

Usage (import):
  from youtube_downloader import download_youtube
  download_youtube(url, output_path='.', filename='video.mp4')
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import subprocess
import shutil
from typing import Callable, Optional

# Default download directory requested by the user
DOWNLOAD_DIR = "/Users/tarun_bhardwaj/mydrive/youTubevideo"

try:
    from pytube import YouTube
except Exception as exc:  # pragma: no cover - user environment
    YouTube = None

# Optional fallback using yt-dlp via subprocess for robustness
def _download_with_ytdlp(url: str, output_path: str, filename: Optional[str] = None, cookies: Optional[str] = None) -> str:
    """Fallback downloader using yt-dlp CLI. Returns absolute path to saved file."""
    # Build output template
    os.makedirs(output_path, exist_ok=True)
    if filename:
        out_template = os.path.join(output_path, filename)
    else:
        out_template = os.path.join(output_path, '%(title)s.%(ext)s')

    # ffmpeg availability should already be checked and PATH set by caller
    ffmpeg_path = shutil.which("ffmpeg")
    has_ffmpeg = ffmpeg_path is not None

    # Request yt-dlp to merge best video + best audio into an MP4 when possible.
    # Add flags to improve robustness for restricted/geoblocked content and
    # capture stderr/stdout for better diagnostics.
    yt_dlp_exe = shutil.which("yt-dlp")
    if yt_dlp_exe:
        base_cmd = [
            yt_dlp_exe,
            "-o", out_template,
        ]
    else:
        base_cmd = [
            sys.executable, "-m", "yt_dlp",
            "-o", out_template,
        ]
    base_cmd.extend([
        # Try to bypass geo-restrictions and ignore certificate issues if present
        "--geo-bypass",
        "--no-check-certificate",
        # Provide a common browser UA to avoid trivial bot blocks
        "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        # Let yt-dlp auto-select the best client strategy
        # (defaults to trying android, ios, web in order based on availability)
    ])

    if has_ffmpeg:
        base_cmd.extend([
            "--merge-output-format", "mp4",
            "--hls-prefer-ffmpeg",
            "--ffmpeg-location", ffmpeg_path  # Explicitly tell yt-dlp where ffmpeg is
        ])
    else:
        # Native muxing avoids ffmpeg requirement; yt-dlp will warn if merging isn't possible
        base_cmd.append("--hls-prefer-native")

    # If a cookies file is provided (exported from your browser), pass it to yt-dlp
    if cookies:
        base_cmd.extend(["--cookies", cookies])

    # Try progressively simpler format selections to avoid 403/unsupported combos.
    # Priority: 1080p with audio merge, fallback to 720p, then any quality
    format_candidates = [
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]",
        "bestvideo*+bestaudio/best",
        "bv*[ext=mp4]+ba[ext=m4a]/best[ext=mp4]/best",
        "22/18/best",
    ]

    # Pass the modified environment with ffmpeg PATH to subprocess
    env = os.environ.copy()
    
    last_exc: Optional[Exception] = None
    for fmt in format_candidates:
        cmd = base_cmd + ["-f", fmt, url]
        for attempt in range(1, 3):
            try:
                proc = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
                if proc.returncode == 0:
                    last_exc = None
                    break
                last_exc = RuntimeError(
                    f"yt-dlp failed (format {fmt}, attempt {attempt}): returncode={proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
                )
            except Exception as exc:
                last_exc = exc
        if last_exc is None:
            break

    if last_exc is not None:
        raise RuntimeError(f"yt-dlp fallback failed after retries: {last_exc}") from last_exc

    # If filename provided, return that path; otherwise try to find the file
    if filename:
        return os.path.abspath(os.path.join(output_path, filename))
    # Attempt to find the most recently modified file in output_path
    candidates = sorted(
        (os.path.join(output_path, p) for p in os.listdir(output_path)),
        key=lambda p: os.path.getmtime(p),
        reverse=True,
    )
    return os.path.abspath(candidates[0]) if candidates else os.path.abspath(output_path)


def _sanitize_filename(name: str) -> str:
    """Make a filesystem-safe filename from a video title."""
    name = name.strip()
    # Replace path separators and control chars
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name)
    return name


def _check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available, adding venv bin to PATH if needed."""
    # First check if already in PATH
    if shutil.which("ffmpeg") is not None:
        return True
    
    # Try to find ffmpeg in venv and add to PATH
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    venv_bin = os.path.join(project_root, '.venv', 'bin')
    
    if os.path.isdir(venv_bin) and venv_bin not in os.environ.get('PATH', ''):
        os.environ['PATH'] = venv_bin + os.pathsep + os.environ.get('PATH', '')
    
    return shutil.which("ffmpeg") is not None


def download_youtube(
    url: str,
    output_path: str = DOWNLOAD_DIR,
    filename: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    cookies: Optional[str] = None,
) -> str:
    """Download a YouTube video to `output_path` and return the saved file path.

    Parameters
    - url: full YouTube video URL
    - output_path: directory where the file will be saved
    - filename: optional filename to use (including extension). If not provided,
      a sanitized title from the video will be used with MP4 extension.
    - progress_callback: optional function called as progress_callback(received_bytes, total_bytes)

    Raises
    - RuntimeError if pytube is not installed or download fails.
    """
    if YouTube is None:
        raise RuntimeError(
            "pytube is not available. Install with: pip install pytube"
        )

    if not url or not isinstance(url, str):
        raise ValueError("A valid YouTube URL must be provided")

    # Check ffmpeg availability and add to PATH if in venv
    has_ffmpeg = _check_ffmpeg_available()
    
    # If ffmpeg is available, prefer yt-dlp for highest quality (1080p+)
    # Progressive streams from pytube max out at 720p
    if has_ffmpeg:
        return _download_with_ytdlp(url, output_path=output_path, filename=filename, cookies=cookies)
    
    # Try pytube first, but fall back to yt-dlp if any step fails
    try:
        yt = YouTube(url)
        
        # Otherwise, try pytube progressive streams as fallback
        progressive_streams = list(yt.streams.filter(progressive=True, file_extension="mp4"))
        if progressive_streams:
            # Sort by resolution first, then filesize for best quality
            progressive_streams.sort(
                key=lambda s: (getattr(s, "resolution", "0p").rstrip("p") if hasattr(s, "resolution") else 0, 
                              getattr(s, "filesize", 0) or 0),
                reverse=True
            )
            stream = progressive_streams[0]
        else:
            stream = None

        if stream is None:
            # No suitable progressive mp4 stream available through pytube.
            # Let yt-dlp handle bestvideo+bestaudio selection and merging.
            return _download_with_ytdlp(url, output_path=output_path, filename=filename, cookies=cookies)

        title = _sanitize_filename(yt.title or yt.video_id)
        if filename:
            save_name = filename
        else:
            save_name = f"{title}.mp4"

        # Ensure output dir exists
        os.makedirs(output_path, exist_ok=True)

        dest_path = os.path.join(output_path, save_name)

        # Define internal callback to adapt pytube progress events
        def _pytube_progress(stream_obj, chunk, bytes_remaining):
            try:
                total = stream_obj.filesize
            except Exception:
                total = None
            received = total - bytes_remaining if total is not None else None
            if progress_callback:
                try:
                    progress_callback(received or 0, total or 0)
                except Exception:
                    pass

        # Attach callback if supported
        try:
            yt.register_on_progress_callback(_pytube_progress)
        except Exception:
            # older/newer pytube versions may vary; ignore if not supported
            pass

        # Download using pytube (progressive stream with audio)
        stream.download(output_path=output_path, filename=save_name)
        return os.path.abspath(dest_path)
    except Exception as exc:
        # Attempt fallback using yt-dlp if available
        try:
            return _download_with_ytdlp(url, output_path=output_path, filename=filename, cookies=cookies)
        except Exception as fallback_exc:
            # If fallback also fails, raise original exception context for debugging
            raise RuntimeError(f"pytube failed: {exc}; yt-dlp fallback: {fallback_exc}") from exc


# Simple CLI so this script only runs when explicitly invoked
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download a YouTube video (safe, importable tool)")
    parser.add_argument("--url", required=False, help="YouTube video URL to download")
    parser.add_argument("--output", default=DOWNLOAD_DIR, help="Output directory")
    parser.add_argument("--filename", default=None, help="Optional filename to save as (including extension)")
    parser.add_argument("--cookies", default=None, help="Optional path to browser cookies.txt for age/region-restricted videos")
    args = parser.parse_args()
    # If URL not provided via CLI, prompt the user (interactive)
    url = args.url
    if not url:
        try:
            # Use input() so the script blocks and asks for URL when run interactively
            url = input("Enter YouTube URL: ").strip()
        except EOFError:
            url = None

    if YouTube is None:
        print("Error: pytube is not installed. Install with: pip install pytube", file=sys.stderr)
        sys.exit(2)

    if not url:
        print("No URL provided. Exiting.", file=sys.stderr)
        sys.exit(2)

    try:
        print(f"Downloading: {url}")
        saved = download_youtube(url, output_path=args.output, filename=args.filename, cookies=args.cookies)
        print(f"Downloaded to: {saved}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
