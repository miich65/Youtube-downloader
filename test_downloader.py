"""
Unit tests for downloader.py.

All network calls and file-system side-effects are mocked so the tests run
fully offline.
"""

import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call

# Make sure the project root is on sys.path regardless of how tests are run.
sys.path.insert(0, os.path.dirname(__file__))

import downloader


class TestPromptUrl(unittest.TestCase):
    """Tests for prompt_url()."""

    def test_returns_stripped_url(self):
        with patch("builtins.input", return_value="  https://youtu.be/abc  "):
            result = downloader.prompt_url()
        self.assertEqual(result, "https://youtu.be/abc")

    def test_exits_on_empty_input(self):
        with patch("builtins.input", return_value="  "):
            with self.assertRaises(SystemExit):
                downloader.prompt_url()


class TestPromptOutputDir(unittest.TestCase):
    """Tests for prompt_output_dir()."""

    def test_returns_provided_directory(self):
        with patch("builtins.input", return_value="/tmp/videos"):
            result = downloader.prompt_output_dir()
        self.assertEqual(result, "/tmp/videos")

    def test_defaults_to_current_directory(self):
        with patch("builtins.input", return_value=""):
            result = downloader.prompt_output_dir()
        self.assertEqual(result, ".")


class TestPromptCookiesFromBrowser(unittest.TestCase):
    """Tests for prompt_cookies_from_browser()."""

    def test_returns_none_on_empty(self):
        with patch("builtins.input", return_value=""):
            result = downloader.prompt_cookies_from_browser()
        self.assertIsNone(result)

    def test_returns_browser_name_lowercase(self):
        with patch("builtins.input", return_value="Chrome"):
            result = downloader.prompt_cookies_from_browser()
        self.assertEqual(result, "chrome")

    def test_returns_none_and_warns_on_unknown_browser(self):
        with patch("builtins.input", return_value="unknownbrowser"), \
             patch("sys.stderr", new_callable=io.StringIO) as mock_err:
            result = downloader.prompt_cookies_from_browser()
        self.assertIsNone(result)
        self.assertIn("not a recognised browser", mock_err.getvalue())

    def test_all_supported_browsers_accepted(self):
        for browser in downloader._SUPPORTED_BROWSERS:
            with patch("builtins.input", return_value=browser):
                result = downloader.prompt_cookies_from_browser()
            self.assertEqual(result, browser)


class TestGetVideoInfo(unittest.TestCase):
    """Tests for get_video_info()."""

    def _make_ydl_mock(self, info: dict):
        """Return a context-manager mock that yields a YoutubeDL-like object."""
        ydl_instance = MagicMock()
        ydl_instance.extract_info.return_value = info
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=ydl_instance)
        cm.__exit__ = MagicMock(return_value=False)
        return cm, ydl_instance

    def test_returns_info_dict(self):
        fake_info = {"title": "Test Video", "duration": 120, "uploader": "Tester"}
        cm, ydl_instance = self._make_ydl_mock(fake_info)

        with patch("downloader.yt_dlp.YoutubeDL", return_value=cm):
            result = downloader.get_video_info("https://youtu.be/test")

        self.assertEqual(result, fake_info)
        ydl_instance.extract_info.assert_called_once_with(
            "https://youtu.be/test", download=False
        )

    def test_skip_download_option_is_set(self):
        cm, _ = self._make_ydl_mock({})
        captured_opts = {}

        def fake_ydl(opts):
            captured_opts.update(opts)
            return cm

        with patch("downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl):
            downloader.get_video_info("https://youtu.be/test")

        self.assertTrue(captured_opts.get("skip_download"))

    def test_tv_embedded_player_client_is_first(self):
        cm, _ = self._make_ydl_mock({})
        captured_opts = {}

        def fake_ydl(opts):
            captured_opts.update(opts)
            return cm

        with patch("downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl):
            downloader.get_video_info("https://youtu.be/test")

        clients = captured_opts["extractor_args"]["youtube"]["player_client"]
        self.assertEqual(clients[0], "tv_embedded")

    def test_cookies_from_browser_passed_when_provided(self):
        cm, _ = self._make_ydl_mock({})
        captured_opts = {}

        def fake_ydl(opts):
            captured_opts.update(opts)
            return cm

        with patch("downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl):
            downloader.get_video_info("https://youtu.be/test", cookies_from_browser="firefox")

        self.assertEqual(captured_opts.get("cookiesfrombrowser"), ("firefox",))

    def test_no_cookies_key_when_not_provided(self):
        cm, _ = self._make_ydl_mock({})
        captured_opts = {}

        def fake_ydl(opts):
            captured_opts.update(opts)
            return cm

        with patch("downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl):
            downloader.get_video_info("https://youtu.be/test")

        self.assertNotIn("cookiesfrombrowser", captured_opts)


class TestDownloadVideo(unittest.TestCase):
    """Tests for download_video()."""

    def _make_ydl_mock(self):
        ydl_instance = MagicMock()
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=ydl_instance)
        cm.__exit__ = MagicMock(return_value=False)
        return cm, ydl_instance

    def test_calls_ydl_download_with_url(self):
        cm, ydl_instance = self._make_ydl_mock()
        url = "https://youtu.be/test"

        with patch("downloader.yt_dlp.YoutubeDL", return_value=cm), \
             patch("os.makedirs"):
            downloader.download_video(url, "/tmp/out")

        ydl_instance.download.assert_called_once_with([url])

    def test_creates_output_directory(self):
        cm, _ = self._make_ydl_mock()

        with patch("downloader.yt_dlp.YoutubeDL", return_value=cm), \
             patch("os.makedirs") as mock_makedirs:
            downloader.download_video("https://youtu.be/test", "/tmp/out")

        mock_makedirs.assert_called_once_with("/tmp/out", exist_ok=True)

    def test_output_template_uses_output_dir(self):
        cm, _ = self._make_ydl_mock()
        captured_opts = {}

        def fake_ydl(opts):
            captured_opts.update(opts)
            return cm

        with patch("downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl), \
             patch("os.makedirs"):
            downloader.download_video("https://youtu.be/test", "/my/dir")

        self.assertIn("/my/dir", captured_opts["outtmpl"])

    def test_cookies_from_browser_forwarded_to_ydl(self):
        cm, _ = self._make_ydl_mock()
        captured_opts = {}

        def fake_ydl(opts):
            captured_opts.update(opts)
            return cm

        with patch("downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl), \
             patch("os.makedirs"):
            downloader.download_video("https://youtu.be/test", "/tmp/out", cookies_from_browser="chrome")

        self.assertEqual(captured_opts.get("cookiesfrombrowser"), ("chrome",))


class TestMain(unittest.TestCase):
    """Integration-style tests for main() using mocks."""

    def _run_main(self, inputs, info=None, download_side_effect=None):
        """Run main() feeding *inputs* to input() one by one."""
        if info is None:
            info = {"title": "My Video", "duration": 60, "uploader": "Author"}

        input_iter = iter(inputs)

        with patch("builtins.input", side_effect=input_iter), \
             patch("downloader.get_video_info", return_value=info) as mock_info, \
             patch("downloader.download_video", side_effect=download_side_effect) as mock_dl:
            downloader.main()

        return mock_info, mock_dl

    def test_full_happy_path(self):
        inputs = [
            "https://youtu.be/abc",  # URL
            "",                       # output dir (current)
            "",                       # browser cookies (skip)
            "y",                      # confirm download
        ]
        mock_info, mock_dl = self._run_main(inputs)
        mock_info.assert_called_once_with("https://youtu.be/abc", None)
        mock_dl.assert_called_once_with("https://youtu.be/abc", ".", None)

    def test_full_happy_path_with_browser_cookies(self):
        inputs = [
            "https://youtu.be/abc",  # URL
            "",                       # output dir (current)
            "firefox",                # browser cookies
            "y",                      # confirm download
        ]
        mock_info, mock_dl = self._run_main(inputs)
        mock_info.assert_called_once_with("https://youtu.be/abc", "firefox")
        mock_dl.assert_called_once_with("https://youtu.be/abc", ".", "firefox")

    def test_download_cancelled_on_no(self):
        inputs = [
            "https://youtu.be/abc",  # URL
            "",                       # output dir (current)
            "",                       # browser cookies (skip)
            "n",                      # cancel download
        ]
        _, mock_dl = self._run_main(inputs)
        mock_dl.assert_not_called()

    def test_exits_on_download_error(self):
        import yt_dlp
        inputs = [
            "https://youtu.be/abc",  # URL
            "",                       # output dir (current)
            "",                       # browser cookies (skip)
            "y",                      # confirm download
        ]
        with self.assertRaises(SystemExit):
            self._run_main(inputs, download_side_effect=yt_dlp.utils.DownloadError("fail"))

    def test_exits_on_info_fetch_error(self):
        import yt_dlp
        inputs = [
            "https://youtu.be/abc",  # URL
            "",                       # output dir (current)
            "",                       # browser cookies (skip)
        ]
        with patch("builtins.input", side_effect=iter(inputs)), \
             patch("downloader.get_video_info",
                   side_effect=yt_dlp.utils.DownloadError("not found")):
            with self.assertRaises(SystemExit):
                downloader.main()


if __name__ == "__main__":
    unittest.main()

