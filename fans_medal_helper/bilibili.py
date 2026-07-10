import asyncio
import hashlib
import json
import random
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import aiohttp
from curl_cffi.requests import AsyncSession

from .config import AccountConfig
from .models import Medal


APP_KEY = "4409e2ce8ffd12b8"
APP_SECRET = "59b43e04ad6965f34319062b478f83dd"
APP_HEADERS = {
    "User-Agent": "Mozilla/5.0 BiliDroid/6.73.1 (bbcallen@gmail.com) os/android model/Mi 10 Pro mobi_app/android build/6731100 channel/xiaomi innerVer/6731110 osVer/12 network/2",
    "Content-Type": "application/x-www-form-urlencoded",
}
EMOTES = ("[花]", "[比心]")


class BilibiliError(RuntimeError):
    pass


@dataclass
class BilibiliClient:
    account: AccountConfig
    timeout_seconds: int

    def __post_init__(self) -> None:
        self.session: AsyncSession | None = None
        self.mid = 0
        self.buvid3 = ""
        self._heartbeat_session = str(uuid.uuid4())

    async def __aenter__(self) -> "BilibiliClient":
        self.session = AsyncSession(max_clients=10, impersonate="chrome131")
        try:
            await self.login()
        except Exception:
            await self.session.close()
            self.session = None
            raise
        return self

    async def __aexit__(self, *_: object) -> None:
        if self.session:
            await self.session.close()

    async def login(self) -> None:
        payload = await self._get("https://app.bilibili.com/x/v2/account/mine", signed=True)
        self.mid = int(payload["mid"])
        if self.mid <= 0:
            raise BilibiliError("B 站登录验证失败")
        fingerprint = await self._get("https://api.bilibili.com/x/frontend/finger/spi", signed=False)
        self.buvid3 = fingerprint.get("b_3", "")

    async def live_medals(self) -> list[Medal]:
        return [medal async for medal in self._medals() if medal.live_status]

    async def like(self, medal: Medal, click_count: int) -> None:
        await self._post(
            "https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3",
            {
                "click_time": click_count,
                "room_id": medal.room_id,
                "anchor_id": medal.anchor_id,
                "uid": self.mid,
            },
            headers=self._headers(),
        )

    async def heartbeat(self, medal: Medal) -> None:
        now = int(time.time())
        start_of_day = int(time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d")))
        started_at = max(start_of_day, now - 60)
        payload = {
            "platform": "android",
            "uuid": self._heartbeat_session,
            "buvid": _random_token(37).upper(),
            "seq_id": "1",
            "room_id": str(medal.room_id),
            "parent_id": "6",
            "area_id": "283",
            "timestamp": str(started_at),
            "secret_key": "axoaadsffcazxksectbbb",
            "watch_time": str(now - started_at),
            "up_id": str(medal.anchor_id),
            "up_level": "40",
            "jump_from": "30000",
            "gu_id": _random_token(43).lower(),
            "play_type": "0",
            "play_url": "",
            "s_time": "0",
            "data_behavior_id": "",
            "data_source_id": "",
            "up_session": f"l:one:live:record:{medal.room_id}:{now - 88888}",
            "visit_id": _random_token(32).lower(),
            "watch_status": "%7B%22pk_id%22%3A0%2C%22screen_status%22%3A1%7D",
            "click_id": self._heartbeat_session,
            "session_id": "",
            "player_type": "0",
            "client_ts": str(now),
        }
        payload["client_sign"] = _client_sign(payload)
        await self._post(
            "https://live-trace.bilibili.com/xlive/data-interface/v1/heartbeat/mobileHeartBeat",
            payload,
        )

    async def send_danmaku(self, medal: Medal) -> str:
        message = random.choice(EMOTES)
        payload = await self._post(
            "https://api.live.bilibili.com/xlive/app-room/v1/dM/sendmsg",
            {"cid": medal.room_id, "msg": message, "rnd": int(time.time()), "color": "16777215", "fontsize": "25"},
        )
        extra = payload.get("mode_info", {}).get("extra")
        if not extra:
            return message
        return json.loads(extra).get("content", message)

    async def _medals(self) -> AsyncIterator[Medal]:
        page = 1
        while True:
            payload = await self._get(
                "https://api.live.bilibili.com/xlive/app-ucenter/v1/fansMedal/panel",
                {"page": page, "page_size": 50},
                signed=True,
            )
            items = payload.get("list", [])
            for item in items:
                room = item.get("room_info", {})
                medal = item.get("medal", {})
                anchor = item.get("anchor_info", {})
                anchor_id = int(medal.get("target_id", 0))
                room_id = int(room.get("room_id", 0))
                if not anchor_id or not room_id or not self.account.allows(anchor_id):
                    continue
                yield Medal(
                    anchor_id=anchor_id,
                    room_id=room_id,
                    anchor_name=anchor.get("nick_name", str(anchor_id)),
                    live_status=_is_live(room.get("live_status")),
                )
            if not items:
                return
            page += 1

    async def _get(self, url: str, data: dict[str, Any] | None = None, *, signed: bool) -> dict[str, Any]:
        params = self._signed(data or {}) if signed else data or {}
        return await self._request("GET", url, params=params)

    async def _post(self, url: str, data: dict[str, Any], *, headers: dict[str, str] | None = None) -> dict[str, Any]:
        return await self._request("POST", url, data=self._signed(data), headers=headers or dict(APP_HEADERS))

    async def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        if not self.session:
            raise RuntimeError("客户端尚未启动")
        last_error = "unknown error"
        for attempt in range(3):
            try:
                response = await self.session.request(
                    method,
                    url,
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
                response.raise_for_status()
                body = response.json()
                if body.get("code") != 0:
                    raise BilibiliError(body.get("message", "B 站 API 请求失败"))
                return body.get("data", {})
            except (aiohttp.ClientError, asyncio.TimeoutError, BilibiliError) as error:
                last_error = _safe_error(error)
                if attempt == 2:
                    break
                await asyncio.sleep(2**attempt)
        raise BilibiliError(last_error)

    def _signed(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = {**data, "access_key": self.account.access_key, "actionKey": "appkey", "appkey": APP_KEY, "ts": int(time.time())}
        query = urlencode(sorted(payload.items()))
        return {**payload, "sign": hashlib.md5(f"{query}{APP_SECRET}".encode()).hexdigest()}

    def _headers(self) -> dict[str, str]:
        headers = dict(APP_HEADERS)
        headers["x-bili-mid"] = str(self.mid)
        if self.buvid3:
            headers["Cookie"] = f"buvid3={self.buvid3}"
        return headers


def _client_sign(data: dict[str, Any]) -> str:
    result = json.dumps(data, separators=(",", ":"))
    for algorithm in ("sha512", "sha3_512", "sha384", "sha3_384", "blake2b"):
        result = hashlib.new(algorithm, result.encode()).hexdigest()
    return result


def _random_token(length: int) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choices(alphabet, k=length))


def _is_live(value: Any) -> bool:
    return value in (1, "1", True)


def _safe_error(error: Exception) -> str:
    if hasattr(error, "status_code"):
        return f"HTTP {error.status_code}"
    return str(error).split("url=")[0].rstrip(", ")
