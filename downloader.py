#!/usr/bin/env python3
"""
YouTube Video Downloader
Interactive command-line script to download YouTube videos using yt-dlp.
"""

import sys
import os
import yt_dlp


def get_video_info(url: str) -> dict:
    """Return video metadata without downloading."""
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def download_video(url: str, output_dir: str = ".") -> None:
    """Download the best available video+audio for *url* into *output_dir*."""
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


def prompt_url() -> str:
    """Prompt the user for a YouTube URL and return it."""
    url = input("Enter the YouTube video URL: ").strip()
    if not url:
        print("Error: no URL provided.", file=sys.stderr)
        sys.exit(1)
    return url


def prompt_output_dir() -> str:
    """Prompt the user for an output directory (defaults to current directory)."""
    answer = input("Enter output directory [press Enter for current directory]: ").strip()
    return answer if answer else "."


def main() -> None:
    print("=== YouTube Video Downloader ===\n")

    url = prompt_url()
    output_dir = prompt_output_dir()

    print(f"\nFetching video info for: {url}")
    try:
        info = get_video_info(url)
        print(f"Title   : {info.get('title', 'N/A')}")
        print(f"Duration: {info.get('duration', 0)} seconds")
        print(f"Uploader: {info.get('uploader', 'N/A')}\n")
    except yt_dlp.utils.DownloadError as exc:
        print(f"Error fetching video info: {exc}", file=sys.stderr)
        sys.exit(1)

    confirm = input("Start download? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("Download cancelled.")
        return

    print("\nDownloading …")
    try:
        download_video(url, output_dir)
        print("\nDownload complete!")
    except yt_dlp.utils.DownloadError as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
