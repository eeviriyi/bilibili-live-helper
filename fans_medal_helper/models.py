from dataclasses import dataclass


@dataclass(frozen=True)
class Medal:
    anchor_id: int
    room_id: int
    medal_id: int
    anchor_name: str


@dataclass(frozen=True)
class LiveRoom:
    anchor_id: int
    room_id: int
    anchor_name: str


@dataclass(frozen=True)
class TaskSettings:
    poll_interval: int = 120
    watching_minutes: int = 30
    heartbeat_interval: int = 60
    danmaku_count: int = 10
    danmaku_interval: int = 180
