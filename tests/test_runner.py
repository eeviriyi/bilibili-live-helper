from datetime import date

import pytest

from fans_medal_helper.models import LiveRoom, Medal, TaskSettings
from fans_medal_helper.runner import LiveTaskRunner


class FakeClient:
    def __init__(self):
        self.medals = [Medal(anchor_id=1, room_id=101, medal_id=11, anchor_name="Alpha")]
        self.live_rooms = [
            LiveRoom(anchor_id=1, room_id=101, anchor_name="Alpha"),
            LiveRoom(anchor_id=2, room_id=102, anchor_name="No medal"),
        ]
        self.likes = 0
        self.heartbeats = 0
        self.danmakus = 0
        self.closed = False

    async def list_medals(self):
        return self.medals

    async def list_live_rooms(self):
        return self.live_rooms

    async def like(self, medal):
        self.likes += 1

    async def heartbeat(self, medal):
        self.heartbeats += 1

    async def send_danmaku(self, medal):
        self.danmakus += 1
        return "[花]"

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_runs_each_live_medal_once_per_day():
    client = FakeClient()
    current_day = [date(2026, 7, 10)]

    async def no_sleep(_):
        return None

    runner = LiveTaskRunner(
        client,
        TaskSettings(watching_minutes=3, danmaku_count=2),
        sleep=no_sleep,
        today=lambda: current_day[0],
        log=lambda _: None,
    )
    await runner.initialize()

    tasks = await runner.run_once()
    await __import__("asyncio").gather(*tasks)
    assert (client.likes, client.heartbeats, client.danmakus) == (1, 3, 2)

    assert await runner.run_once() == []
    assert (client.likes, client.heartbeats, client.danmakus) == (1, 3, 2)

    current_day[0] = date(2026, 7, 11)
    tasks = await runner.run_once()
    await __import__("asyncio").gather(*tasks)
    assert (client.likes, client.heartbeats, client.danmakus) == (2, 6, 4)
