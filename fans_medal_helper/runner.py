import asyncio
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Protocol

from .models import LiveRoom, Medal, TaskSettings


class LiveClient(Protocol):
    async def list_medals(self) -> list[Medal]: ...
    async def list_live_rooms(self) -> list[LiveRoom]: ...
    async def like(self, medal: Medal) -> None: ...
    async def heartbeat(self, medal: Medal) -> None: ...
    async def send_danmaku(self, medal: Medal) -> str: ...
    async def close(self) -> None: ...


Logger = Callable[[str], None]
Sleep = Callable[[float], Awaitable[None]]


class LiveTaskRunner:
    def __init__(self, client: LiveClient, settings: TaskSettings, *, sleep: Sleep = asyncio.sleep, today: Callable[[], date] = date.today, log: Logger = print):
        self.client = client
        self.settings = settings
        self.sleep = sleep
        self.today = today
        self.log = log
        self.medals: dict[int, Medal] = {}
        self.completed_today: set[int] = set()
        self.day: date | None = None

    async def initialize(self) -> None:
        self.medals = {medal.anchor_id: medal for medal in await self.client.list_medals()}
        self.log(f"已加载 {len(self.medals)} 个粉丝牌")

    def reset_daily_state(self) -> None:
        current_day = self.today()
        if current_day != self.day:
            self.day = current_day
            self.completed_today.clear()
            self.log(f"已重置每日开播任务状态：{current_day.isoformat()}")

    async def run_once(self) -> list[asyncio.Task[None]]:
        self.reset_daily_state()
        tasks: list[asyncio.Task[None]] = []
        for live_room in await self.client.list_live_rooms():
            medal = self.medals.get(live_room.anchor_id)
            if medal is None or medal.anchor_id in self.completed_today:
                continue
            self.completed_today.add(medal.anchor_id)
            self.log(f"检测到 {live_room.anchor_name} 开播，开始本日粉丝牌任务")
            tasks.append(asyncio.create_task(self.run_room(medal)))
        return tasks

    async def run_forever(self) -> None:
        await self.initialize()
        try:
            while True:
                await self.run_once()
                await self.sleep(self.settings.poll_interval)
        finally:
            await self.client.close()

    async def run_room(self, medal: Medal) -> None:
        try:
            await self.client.like(medal)
            self.log(f"{medal.anchor_name} 开播点赞完成（300 次）")
            await asyncio.gather(self.watch_live(medal), self.send_danmaku(medal))
            self.log(f"{medal.anchor_name} 本次开播任务完成")
        except Exception as error:
            self.log(f"{medal.anchor_name} 开播任务失败: {error}")

    async def watch_live(self, medal: Medal) -> None:
        for heartbeat_number in range(1, self.settings.watching_minutes + 1):
            await self.client.heartbeat(medal)
            if heartbeat_number < self.settings.watching_minutes:
                await self.sleep(self.settings.heartbeat_interval)

    async def send_danmaku(self, medal: Medal) -> None:
        for message_number in range(1, self.settings.danmaku_count + 1):
            await self.client.send_danmaku(medal)
            if message_number < self.settings.danmaku_count:
                await self.sleep(self.settings.danmaku_interval)
