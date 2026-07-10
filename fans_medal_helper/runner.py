import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, date
from typing import Protocol
from zoneinfo import ZoneInfo

from .models import Medal, TaskSettings
from .notify import Notifier


SHANGHAI = ZoneInfo("Asia/Shanghai")
Sleep = Callable[[float], Awaitable[None]]


class LiveClient(Protocol):
    async def live_medals(self) -> list[Medal]: ...
    async def like(self, medal: Medal) -> None: ...
    async def heartbeat(self, medal: Medal) -> None: ...
    async def send_danmaku(self, medal: Medal) -> str: ...


class LiveTaskRunner:
    def __init__(
        self,
        client: LiveClient,
        settings: TaskSettings,
        *,
        sleep: Sleep = asyncio.sleep,
        today: Callable[[], date] | None = None,
        logger: logging.Logger | None = None,
        notifier: Notifier | None = None,
    ):
        self.client = client
        self.settings = settings
        self.sleep = sleep
        self.today = today or (lambda: datetime.now(SHANGHAI).date())
        self.logger = logger or logging.getLogger(__name__)
        self.notifier = notifier or Notifier()
        self.completed_today: set[int] = set()
        self.active: dict[int, asyncio.Task[None]] = {}
        self.day: date | None = None
        self.stream_semaphore = asyncio.Semaphore(settings.max_concurrent_streams)

    async def run_forever(self) -> None:
        while True:
            try:
                await self.run_once()
            except Exception:
                self.logger.exception("刷新开播状态失败，将在下个轮询周期重试")
            await self.sleep(self.settings.poll_interval_seconds)

    async def run_once(self) -> list[asyncio.Task[None]]:
        self._reset_daily_state()
        tasks: list[asyncio.Task[None]] = []
        for medal in await self.client.live_medals():
            if medal.anchor_id in self.completed_today or medal.anchor_id in self.active:
                continue
            self.logger.info("检测到 %s 开播，开始本日粉丝牌任务", medal.anchor_name)
            task = asyncio.create_task(self._run_room(medal), name=f"live-task-{medal.anchor_id}")
            self.active[medal.anchor_id] = task
            task.add_done_callback(lambda finished, anchor_id=medal.anchor_id: self._finish(anchor_id, finished))
            tasks.append(task)
        return tasks

    async def _run_room(self, medal: Medal) -> None:
        try:
            async with self.stream_semaphore:
                await self.client.like(medal)
                self.completed_today.add(medal.anchor_id)
                self.logger.info("%s 开播点赞完成（300 次）", medal.anchor_name)
                results = await asyncio.gather(
                    self._watch_live(medal),
                    self._send_danmaku(medal),
                    return_exceptions=True,
                )
        except Exception as error:
            await self._notify("开播任务失败", f"{medal.anchor_name}: {error}", "warning")
            raise

        errors = [result for result in results if isinstance(result, Exception)]
        if errors:
            for error in errors:
                self.logger.error("%s 的后续任务失败: %s", medal.anchor_name, error)
            await self._notify("开播任务部分失败", f"{medal.anchor_name}: {errors[0]}", "warning")
            return

        self.logger.info("%s 本次开播任务完成", medal.anchor_name)
        await self._notify("开播任务完成", f"{medal.anchor_name} 的点赞、观看和应援弹幕任务已完成", "white_check_mark")

    async def _watch_live(self, medal: Medal) -> None:
        for heartbeat_number in range(1, self.settings.watch_minutes + 1):
            await self.client.heartbeat(medal)
            if heartbeat_number < self.settings.watch_minutes:
                await self.sleep(self.settings.heartbeat_interval_seconds)

    async def _send_danmaku(self, medal: Medal) -> None:
        for message_number in range(1, self.settings.danmaku_count + 1):
            message = await self.client.send_danmaku(medal)
            self.logger.info("%s 应援弹幕 %s/%s: %s", medal.anchor_name, message_number, self.settings.danmaku_count, message)
            if message_number < self.settings.danmaku_count:
                await self.sleep(self.settings.danmaku_interval_seconds)

    def _reset_daily_state(self) -> None:
        current_day = self.today()
        if current_day != self.day:
            self.day = current_day
            self.completed_today.clear()
            self.logger.info("已重置每日开播任务状态：%s", current_day.isoformat())

    def _finish(self, anchor_id: int, task: asyncio.Task[None]) -> None:
        self.active.pop(anchor_id, None)
        if task.cancelled():
            self.logger.warning("主播 %s 的开播任务已取消", anchor_id)
            return
        error = task.exception()
        if error:
            self.logger.error("主播 %s 的开播任务失败: %s", anchor_id, error)

    async def _notify(self, title: str, message: str, tags: str) -> None:
        try:
            await self.notifier.publish(title, message, tags=tags)
        except Exception:
            self.logger.exception("通知模块异常")
