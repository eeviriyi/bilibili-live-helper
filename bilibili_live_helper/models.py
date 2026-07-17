from dataclasses import dataclass


@dataclass(frozen=True)
class LiveRoom:
    anchor_id: int
    room_id: int
    anchor_name: str
    title: str
    area_id: int
    parent_area_id: int
