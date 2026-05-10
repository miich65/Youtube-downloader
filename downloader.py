#!/usr/bin/env python3
"""
YouTube Video Downloader
Interactive command-line script to download YouTube videos using yt-dlp.
"""

import sys
import os
import yt_dlp

# Player clients tried in order. tv_embedded and web_creator bypass the
# "Sign in to confirm you're not a bot" error on most public videos without
# requiring the user to be logged in.
_PLAYER_CLIENTS = ["tv_embedded", "web_creator", "ios", "android"]

_SUPPORTED_BROWSERS = ["chrome", "firefox", "edge", "safari", "opera", "brave", "chromium", "vivaldi"]


def _base_opts(cookies_from_browser: str | None = None) -> dict:
    """Return yt-dlp options shared by info fetching and downloading."""
    opts: dict = {
        "extractor_args": {"youtube": {"player_client": _PLAYER_CLIENTS}},
    }
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)
    return opts


def get_video_info(url: str, cookies_from_browser: str | None = None) -> dict:
    """Return video metadata without downloading."""
    opts = _base_opts(cookies_from_browser)
    opts.update(
        {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
    )
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def download_video(
    url: str, output_dir: str = ".", cookies_from_browser: str | None = None
) -> None:
    """Download the best available video+audio for *url* into *output_dir*."""
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    opts = _base_opts(cookies_from_browser)
    opts.update(
        {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": False,
            "no_warnings": False,
        }
    )
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


def prompt_cookies_from_browser() -> str | None:
    """Optionally ask the user which browser to pull cookies from.

    Passing browser cookies lets yt-dlp authenticate with YouTube using the
    user's existing session, which bypasses bot-detection for age-restricted or
    otherwise restricted videos.  Pressing Enter skips this step.
    """
    browsers = ", ".join(_SUPPORTED_BROWSERS)
    answer = input(
        f"Browser for cookies (optional, helps bypass bot-checks) [{browsers}] "
        "or press Enter to skip: "
    ).strip().lower()
    if not answer:
        return None
    if answer not in _SUPPORTED_BROWSERS:
        print(
            f"Warning: '{answer}' is not a recognised browser; skipping cookie extraction.",
            file=sys.stderr,
        )
        return None
    return answer


def main() -> None:
    print("=== YouTube Video Downloader ===\n")

    url = prompt_url()
    output_dir = prompt_output_dir()
    cookies_from_browser = prompt_cookies_from_browser()

    print(f"\nFetching video info for: {url}")
    try:
        info = get_video_info(url, cookies_from_browser)
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
        download_video(url, output_dir, cookies_from_browser)
        print("\nDownload complete!")
    except yt_dlp.utils.DownloadError as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
