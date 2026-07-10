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
    api_interval_seconds: int = 1
    like_clicks_per_request: int = 30
    like_request_count: int = 10
    like_interval_seconds: int = 4
    watch_minutes: int = 30
    heartbeat_interval_seconds: int = 60
    danmaku_count: int = 10
    danmaku_interval_seconds: int = 180
    global_danmaku_interval_seconds: int = 3
