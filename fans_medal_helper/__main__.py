import asyncio
import logging
from pathlib import Path

from .bilibili import BilibiliClient
from .config import AccountConfig, Settings, load_settings
from .models import TaskSettings
from .notify import NtfyNotifier, Notifier
from .runner import LiveTaskRunner


async def run_account(account: AccountConfig, settings: Settings, notifier: Notifier) -> None:
    task_settings = TaskSettings(
        poll_interval_seconds=settings.poll_interval_seconds,
        max_concurrent_streams=settings.max_concurrent_streams,
        watch_minutes=settings.watch_minutes,
        heartbeat_interval_seconds=settings.heartbeat_interval_seconds,
        danmaku_count=settings.danmaku_count,
        danmaku_interval_seconds=settings.danmaku_interval_seconds,
    )
    async with BilibiliClient(account, settings.request_timeout_seconds) as client:
        await LiveTaskRunner(client, task_settings, notifier=notifier).run_forever()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = load_settings(Path("users.yaml"))
    if settings.ntfy:
        async with NtfyNotifier(settings.ntfy.endpoint, settings.ntfy.token) as notifier:
            await asyncio.gather(*(run_account(account, settings, notifier) for account in settings.accounts))
    else:
        await asyncio.gather(*(run_account(account, settings, Notifier()) for account in settings.accounts))


if __name__ == "__main__":
    asyncio.run(main())
