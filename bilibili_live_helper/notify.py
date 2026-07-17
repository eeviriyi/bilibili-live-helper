import re
from contextlib import AbstractAsyncContextManager
from typing import Protocol

import aiohttp


SEQUENCE_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,80}")


class NotificationError(RuntimeError):
    pass


class NotificationPublisher(Protocol):
    async def publish(
        self, title: str, message: str, *, tags: str, sequence_id: str
    ) -> None: ...


class NtfyNotifier(AbstractAsyncContextManager["NtfyNotifier"]):
    def __init__(self, endpoint: str, token: str | None = None):
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "NtfyNotifier":
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10), trust_env=True
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def publish(
        self, title: str, message: str, *, tags: str, sequence_id: str
    ) -> None:
        if not self.session:
            raise RuntimeError("ntfy notifier is not started")
        validate_sequence_id(sequence_id)
        headers = {"Title": title, "Tags": tags, "X-Sequence-ID": sequence_id}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            async with self.session.post(
                self.endpoint, data=message.encode(), headers=headers
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as error:
            raise NotificationError(
                f"ntfy delivery failed: {type(error).__name__}"
            ) from error


def validate_sequence_id(sequence_id: str) -> None:
    if not SEQUENCE_ID_PATTERN.fullmatch(sequence_id):
        raise ValueError(
            "ntfy sequence ID must contain only letters, numbers, underscores, and hyphens"
        )
