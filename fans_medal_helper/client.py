import json
import os

from src import BiliUser

from .models import LiveRoom, Medal


class BilibiliLiveClient:
    def __init__(self, access_key: str, white_uid: str | int = 0, banned_uid: str | int = 0):
        self.user = BiliUser(access_key, str(white_uid), str(banned_uid), {"CURRENT_CRON_INDEX": 0, "TOTAL_CRON_COUNT": 0, "CRON_INDEX": 0})

    async def login(self) -> None:
        if not await self.user.loginVerify():
            raise RuntimeError("B 站登录失败，请重新获取 access_key")

    async def list_medals(self) -> list[Medal]:
        await self.user.getMedals()
        return [Medal(medal["medal"]["target_id"], medal["room_info"]["room_id"], medal["medal"]["medal_id"], medal["anchor_info"]["nick_name"]) for medal in self.user.medals]

    async def list_live_rooms(self) -> list[LiveRoom]:
        await self.user.getMedals()
        return [
            LiveRoom(
                anchor_id=medal["medal"]["target_id"],
                room_id=medal["room_info"]["room_id"],
                anchor_name=medal["anchor_info"]["nick_name"],
            )
            for medal in self.user.medals
            if medal["room_info"].get("live_status") == 1
        ]

    async def like(self, medal: Medal) -> None:
        await self.user.api.likeInteractV3(medal.room_id, medal.anchor_id, self.user.mid)

    async def heartbeat(self, medal: Medal) -> None:
        await self.user.api.heartbeat(medal.room_id, medal.anchor_id)

    async def send_danmaku(self, medal: Medal) -> str:
        return await self.user.api.sendDanmaku(medal.room_id)

    async def close(self) -> None:
        await self.user.session.close()


def load_config() -> dict:
    if os.environ.get("USERS"):
        return json.loads(os.environ["USERS"])
    import yaml

    with open("users.yaml", "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)
