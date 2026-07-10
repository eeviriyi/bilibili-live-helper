from pathlib import Path

import pytest

from fans_medal_helper.config import load_settings


def test_loads_strict_new_format(tmp_path: Path):
    config = tmp_path / "users.yaml"
    config.write_text(
        """accounts:
  - access_key: key
    include_uids: [1, 2]
poll_interval_seconds: 60
watch_minutes: 30
danmaku_count: 10
""",
        encoding="utf-8",
    )
    settings = load_settings(config)
    assert settings.poll_interval_seconds == 60
    assert settings.like_clicks_per_request == 30
    assert settings.like_request_count == 10
    assert settings.accounts[0].allows(1)
    assert not settings.accounts[0].allows(3)


def test_rejects_empty_accounts(tmp_path: Path):
    config = tmp_path / "users.yaml"
    config.write_text("accounts: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="至少需要"):
        load_settings(config)


def test_loads_optional_ntfy(tmp_path: Path):
    config = tmp_path / "users.yaml"
    config.write_text(
        """accounts:
  - access_key: key
ntfy:
  endpoint: https://ntfy.example/private-topic
  token: secret
""",
        encoding="utf-8",
    )
    settings = load_settings(config)
    assert settings.ntfy is not None
    assert settings.ntfy.endpoint == "https://ntfy.example/private-topic"
