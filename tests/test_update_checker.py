# SPDX-License-Identifier: GPL-3.0-or-later
# LinguaNova: modified work based on RenLocalizer 2.8.19; modification notice date 2026-10-16.
# See LICENSE/COPYING, NOTICE.md and MODIFICATIONS_LINGUANOVA.md.
import unittest
from unittest.mock import patch, MagicMock
from src.utils.update_checker import check_for_updates, _is_newer, _parse_version

class TestUpdateChecker(unittest.TestCase):
    def setUp(self):
        self._patcher = patch.dict("os.environ", {"LINGUANOVA_UPDATE_REPO": "example/linguanova"})
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def test_not_configured_is_reported_without_network(self):
        # The release build sets UPDATE_REPO; the "not configured" path is
        # tested by clearing both the constant and the environment variable.
        with patch.dict("os.environ", {"LINGUANOVA_UPDATE_REPO": ""}), \
                patch("src.utils.update_checker.UPDATE_REPO", ""), patch("requests.get") as mock_get:
            result = check_for_updates("2.8.5")
        mock_get.assert_not_called()
        self.assertFalse(result.update_available)
        self.assertIn("not configured", result.error)

    def test_parse_version(self):
        self.assertEqual(_parse_version("1.2.3"), (1, 2, 3))
        self.assertEqual(_parse_version("v2.8.5"), (2, 8, 5))
        self.assertEqual(_parse_version(""), (0,))
        self.assertEqual(_parse_version(None), (0,))

    def test_is_newer(self):
        self.assertTrue(_is_newer("2.8.6", "2.8.5"))
        self.assertTrue(_is_newer("2.9.0", "2.8.5"))
        self.assertTrue(_is_newer("10.0.0", "2.8.5"))
        self.assertFalse(_is_newer("2.8.5", "2.8.5"))
        self.assertFalse(_is_newer("2.8.4", "2.8.5"))
        self.assertFalse(_is_newer("2.8.5", "2.8.5")) # Same versions

    @patch('requests.get')
    def test_check_for_updates_available(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v2.8.6",
            "html_url": "https://github.com/example/linguanova/releases/tag/v2.8.6"
        }
        mock_get.return_value = mock_response

        result = check_for_updates("2.8.5")
        self.assertTrue(result.update_available)
        self.assertEqual(result.latest_version, "v2.8.6")
        self.assertEqual(result.release_url, "https://github.com/example/linguanova/releases/tag/v2.8.6")
        self.assertNil = result.error

    @patch('requests.get')
    def test_check_for_updates_up_to_date(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v2.8.5",
            "html_url": "https://github.com/example/linguanova/releases/tag/v2.8.5"
        }
        mock_get.return_value = mock_response

        result = check_for_updates("2.8.5")
        self.assertFalse(result.update_available)
        self.assertEqual(result.latest_version, "v2.8.5")

    @patch('requests.get')
    def test_check_for_updates_api_fallback_to_html(self, mock_get):
        # API fails, html parsing succeeds
        mock_api_response = MagicMock()
        mock_api_response.status_code = 404
        
        mock_html_response = MagicMock()
        mock_html_response.status_code = 200
        mock_html_response.text = 'href="/releases/tag/v2.8.6"'
        
        mock_get.side_effect = [mock_api_response, mock_html_response]

        result = check_for_updates("2.8.5")
        self.assertTrue(result.update_available)
        self.assertEqual(result.latest_version, "v2.8.6")

if __name__ == '__main__':
    unittest.main()


def test_backend_reports_a_failed_check_instead_of_up_to_date():
    """A check that never reached GitHub said "You are up to date" (2026-10-18 test)."""
    from types import SimpleNamespace
    from src.backend.app_backend import AppBackend
    from src.utils.update_checker import UpdateCheckResult

    logs, finished = [], []
    stub = SimpleNamespace(
        _version="1.0.0",
        config=SimpleNamespace(get_ui_text=lambda key, default: default),
        logger=MagicMock(),
        logMessage=SimpleNamespace(emit=lambda level, msg: logs.append((level, msg))),
        updateCheckFinished=SimpleNamespace(emit=lambda ok, msg: finished.append((ok, msg))),
        updateAvailable=SimpleNamespace(emit=lambda *a: finished.append(("available", a))),
    )
    failed = UpdateCheckResult("1.0.0", "", False, "", error="HTTP 404")
    with patch("src.utils.update_checker.check_for_updates", return_value=failed):
        AppBackend._check_updates_thread(stub, manual=False)
    assert finished == [(False, "Update check failed: HTTP 404")]
    assert logs and logs[0][0] == "warning" and "HTTP 404" in logs[0][1]
    assert not any("up to date" in msg for _, msg in finished)


def test_update_dialog_texts_match_the_dialog():
    """The dialog said "Press OK to download" but its button is "Download",
    and showed "vv1.0.1" for a "v1.0.1" tag (2026-10-18 test)."""
    import json
    from pathlib import Path

    for path in Path("locales").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        msg, click = data["update_available_msg"], data["update_available_click"]
        assert "{current}" in msg and "{latest}" in msg, path.name
        assert "OK" not in click and "ОК" not in click, path.name

    qml = Path("src/gui/qml/Main.qml").read_text(encoding="utf-8")
    block = qml[qml.index("id: updateDialog"):qml.index("id: updateDialog") + 9000]
    assert 'replace(/^[vV]/, "")' in block
    assert '.replace("{current}"' in block and '.replace("{latest}"' in block
    assert "CloseOnPressOutside" not in block[:600]
