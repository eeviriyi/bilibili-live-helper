from dataclasses import dataclass


@dataclass(frozen=True)
class Medal:
    anchor_id: int
    room_id: int
    anchor_name: str
    live_status: bool


@dataclass(frozen=True)
class TaskSettings:
    poll_interval_seconds: int = 120
    max_concurrent_streams: int = 3
    watch_minutes: int = 30
    heartbeat_interval_seconds: int = 60
    danmaku_count: int = 10
    danmaku_interval_seconds: int = 180
