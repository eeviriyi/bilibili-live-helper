from pathlib import Path

import pytest

from bilibili_live_helper.config import load_settings


def test_loads_single_account_and_preserves_watch_priority(tmp_path: Path):
    config = _write_config(
        tmp_path,
        """access_key: key
include_uids: [1, 2, 3]
watch_uids: [3, 1]
poll_interval_seconds: 60
ntfy:
  endpoint: https://ntfy.example/notifications
  token: secret
""",
    )

    settings = load_settings(config)

    assert settings.access_key == "key"
    assert settings.include_uids == (1, 2, 3)
    assert settings.watch_uids == (3, 1)
    assert settings.poll_interval_seconds == 60
    assert settings.like_clicks_per_request == 30
    assert settings.ntfy is not None
    assert settings.ntfy.endpoint == "https://ntfy.example/notifications"


def test_rejects_removed_multi_account_format(tmp_path: Path):
    config = _write_config(tmp_path, "accounts: []\n")
    with pytest.raises(ValueError, match="Unknown configuration fields: accounts"):
        load_settings(config)


def test_rejects_duplicate_yaml_keys(tmp_path: Path):
    config = _write_config(
        tmp_path,
        """access_key: first
access_key: second
include_uids: [1]
""",
    )
    with pytest.raises(ValueError, match="duplicate key 'access_key'"):
        load_settings(config)


def test_rejects_watch_uid_outside_whitelist(tmp_path: Path):
    config = _write_config(
        tmp_path,
        """access_key: key
include_uids: [1]
watch_uids: [2]
""",
    )
    with pytest.raises(ValueError, match="watch_uids must be included"):
        load_settings(config)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("include_uids", "[]", "include_uids cannot be empty"),
        ("include_uids", "[1, 1]", "cannot contain duplicate"),
        ("like_clicks_per_request", "301", "between 1 and 300"),
        ("watch_minutes", "0", "watch_minutes must be positive"),
    ],
)
def test_rejects_unsafe_values(tmp_path: Path, field: str, value: str, message: str):
    base = {
        "access_key": "key",
        "include_uids": "[1]",
        "watch_uids": "[1]",
        field: value,
    }
    config = _write_config(
        tmp_path, "\n".join(f"{key}: {item}" for key, item in base.items())
    )
    with pytest.raises(ValueError, match=message):
        load_settings(config)


def _write_config(tmp_path: Path, value: str) -> Path:
    path = tmp_path / "users.yaml"
    path.write_text(value, encoding="utf-8")
    return path
