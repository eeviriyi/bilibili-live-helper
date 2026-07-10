from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AccountConfig:
    access_key: str
    include_uids: frozenset[int]
    exclude_uids: frozenset[int]

    def allows(self, anchor_id: int) -> bool:
        if self.include_uids:
            return anchor_id in self.include_uids
        return anchor_id not in self.exclude_uids


@dataclass(frozen=True)
class NtfyConfig:
    endpoint: str
    token: str | None


@dataclass(frozen=True)
class Settings:
    accounts: tuple[AccountConfig, ...]
    poll_interval_seconds: int
    request_timeout_seconds: int
    max_concurrent_streams: int
    watch_minutes: int
    heartbeat_interval_seconds: int
    danmaku_count: int
    danmaku_interval_seconds: int
    ntfy: NtfyConfig | None


def load_settings(path: Path) -> Settings:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("配置根节点必须是 YAML 对象")

    accounts = tuple(_parse_account(value) for value in raw.get("accounts", []))
    if not accounts:
        raise ValueError("至少需要一个 accounts 配置")

    settings = Settings(
        accounts=accounts,
        poll_interval_seconds=_positive(raw, "poll_interval_seconds", 120),
        request_timeout_seconds=_positive(raw, "request_timeout_seconds", 15),
        max_concurrent_streams=_positive(raw, "max_concurrent_streams", 3),
        watch_minutes=_non_negative(raw, "watch_minutes", 30),
        heartbeat_interval_seconds=_positive(raw, "heartbeat_interval_seconds", 60),
        danmaku_count=_non_negative(raw, "danmaku_count", 10),
        danmaku_interval_seconds=_positive(raw, "danmaku_interval_seconds", 180),
        ntfy=_parse_ntfy(raw.get("ntfy")),
    )
    if settings.watch_minutes == 0 and settings.danmaku_count == 0:
        raise ValueError("观看和弹幕不能同时关闭")
    return settings


def _parse_ntfy(value: Any) -> NtfyConfig | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("ntfy 必须是 YAML 对象")
    endpoint = value.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.startswith(("https://", "http://")):
        raise ValueError("ntfy.endpoint 必须是 HTTP(S) 地址")
    token = value.get("token")
    if token is not None and not isinstance(token, str):
        raise ValueError("ntfy.token 必须是字符串")
    return NtfyConfig(endpoint=endpoint, token=token or None)


def _parse_account(value: Any) -> AccountConfig:
    if not isinstance(value, dict):
        raise ValueError("每个 account 必须是 YAML 对象")
    access_key = value.get("access_key")
    if not isinstance(access_key, str) or not access_key.strip():
        raise ValueError("account.access_key 不能为空")
    return AccountConfig(
        access_key=access_key.strip(),
        include_uids=_uid_set(value.get("include_uids", []), "include_uids"),
        exclude_uids=_uid_set(value.get("exclude_uids", []), "exclude_uids"),
    )


def _uid_set(value: Any, field: str) -> frozenset[int]:
    if not isinstance(value, list) or any(not isinstance(uid, int) or uid <= 0 for uid in value):
        raise ValueError(f"{field} 必须是正整数列表")
    return frozenset(value)


def _positive(raw: dict[str, Any], field: str, default: int) -> int:
    value = raw.get(field, default)
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field} 必须是正整数")
    return value


def _non_negative(raw: dict[str, Any], field: str, default: int) -> int:
    value = raw.get(field, default)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} 必须是非负整数")
    return value
