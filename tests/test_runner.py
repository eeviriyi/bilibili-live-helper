import asyncio
from datetime import date

import pytest

from fans_medal_helper.models import Medal, TaskSettings
from fans_medal_helper.runner import LiveTaskRunner


class FakeClient:
    def __init__(self):
        self.live = [Medal(anchor_id=1, room_id=101, anchor_name="Alpha", live_status=True)]
        self.likes = 0
        self.heartbeats = 0
        self.danmakus = 0

    async def live_medals(self):
        return self.live

    async def like(self, medal, click_count):
        assert click_count == 30
        self.likes += 1

    async def heartbeat(self, medal):
        self.heartbeats += 1

    async def send_danmaku(self, medal):
        self.danmakus += 1
        return "[花]"


@pytest.mark.asyncio
async def test_runs_each_live_medal_once_per_day_and_resets_next_day():
    client = FakeClient()
    current_day = [date(2026, 7, 10)]

    async def no_sleep(_):
        return None

    runner = LiveTaskRunner(
        client,
        TaskSettings(watch_minutes=3, danmaku_count=2),
        sleep=no_sleep,
        today=lambda: current_day[0],
        logger=__import__("logging").getLogger("test"),
    )

    tasks = await runner.run_once()
    await asyncio.gather(*tasks)
    assert (client.likes, client.heartbeats, client.danmakus) == (10, 3, 2)

    assert await runner.run_once() == []
    current_day[0] = date(2026, 7, 11)
    tasks = await runner.run_once()
    await asyncio.gather(*tasks)
    assert (client.likes, client.heartbeats, client.danmakus) == (20, 6, 4)


@pytest.mark.asyncio
async def test_failed_like_is_retried_on_the_next_poll():
    class FlakyClient(FakeClient):
        def __init__(self):
            super().__init__()
            self.failed = False

        async def like(self, medal, click_count):
            self.likes += 1
            if not self.failed:
                self.failed = True
                raise RuntimeError("temporary failure")

    client = FlakyClient()

    async def no_sleep(_):
        return None

    runner = LiveTaskRunner(client, TaskSettings(watch_minutes=0, danmaku_count=1), sleep=no_sleep)
    tasks = await runner.run_once()
    await asyncio.gather(*tasks, return_exceptions=True)
    assert client.likes == 1
    assert not runner.completed_today

    tasks = await runner.run_once()
    await asyncio.gather(*tasks)
    assert client.likes == 11
    assert runner.completed_today == {1}
