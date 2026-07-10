import logging
from contextlib import AbstractAsyncContextManager

import aiohttp


class Notifier:
    async def publish(self, title: str, message: str, *, tags: str) -> None:
        return None


class NtfyNotifier(Notifier, AbstractAsyncContextManager["NtfyNotifier"]):
    def __init__(self, endpoint: str, token: str | None = None):
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.session: aiohttp.ClientSession | None = None
        self.logger = logging.getLogger(__name__)

    async def __aenter__(self) -> "NtfyNotifier":
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10), trust_env=True)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self.session:
            await self.session.close()

    async def publish(self, title: str, message: str, *, tags: str) -> None:
        if not self.session:
            raise RuntimeError("ntfy 通知器尚未启动")
        headers = {"Title": title, "Tags": tags}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            async with self.session.post(self.endpoint, data=message.encode(), headers=headers) as response:
                response.raise_for_status()
        except aiohttp.ClientError as error:
            self.logger.warning("ntfy 通知发送失败: %s", error)
