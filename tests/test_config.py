"""Tests for persistent user configuration."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from odds_ticker import config


class ConfigTests(unittest.TestCase):
    def test_load_config_returns_empty_mapping_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch("odds_ticker.config.config_path", return_value=Path(directory) / "missing.json"):
                self.assertEqual(config.load_config(), {})

    def test_save_api_key_creates_file_and_loads_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "config.json"
            with patch("odds_ticker.config.config_path", return_value=path):
                config.save_api_key("  secret-key  ")
                self.assertEqual(config.load_config(), {"api_key": "secret-key"})
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["api_key"], "secret-key")

    def test_save_api_key_preserves_other_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"theme": "dark"}', encoding="utf-8")
            with patch("odds_ticker.config.config_path", return_value=path):
                config.save_api_key("new-key")
                self.assertEqual(config.load_config(), {"theme": "dark", "api_key": "new-key"})


if __name__ == "__main__":
    unittest.main()
