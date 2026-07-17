import asyncio
import logging
import os
import signal
from contextlib import AsyncExitStack
from pathlib import Path

from .bilibili import BilibiliClient
from .config import load_settings
from .notify import NtfyNotifier
from .runner import LiveTaskRunner
from .state import StateStore


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config_path = Path(os.environ.get("BILIBILI_LIVE_HELPER_CONFIG", "users.yaml"))
    state_path = Path(os.environ.get("BILIBILI_LIVE_HELPER_STATE", "data/state.json"))
    settings = load_settings(config_path)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop_event.set)

    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(
            BilibiliClient(
                access_key=settings.access_key,
                timeout_seconds=settings.request_timeout_seconds,
                request_interval_seconds=settings.api_interval_seconds,
            )
        )
        notifier = (
            await stack.enter_async_context(
                NtfyNotifier(settings.ntfy.endpoint, settings.ntfy.token)
            )
            if settings.ntfy
            else None
        )
        runner = LiveTaskRunner(
            client,
            settings,
            StateStore(state_path),
            notifier=notifier,
        )
        await runner.run_forever(stop_event)


if __name__ == "__main__":
    asyncio.run(main())
