import asyncio

from .client import BilibiliLiveClient, load_config
from .models import TaskSettings
from .runner import LiveTaskRunner


async def run_account(account: dict, settings: TaskSettings) -> None:
    client = BilibiliLiveClient(account["access_key"], account.get("white_uid", 0), account.get("banned_uid", 0))
    await client.login()
    await LiveTaskRunner(client, settings).run_forever()


async def main() -> None:
    config = load_config()
    settings = TaskSettings(
        poll_interval=config.get("LIVE_POLL_INTERVAL", 120),
        watching_minutes=config.get("WATCHINGLIVE", 30),
        heartbeat_interval=config.get("WATCHINGLIVE_CD", 60),
        danmaku_count=config.get("DANMAKU_COUNT", 10),
        danmaku_interval=config.get("DANMAKU_CD", 180),
    )
    accounts = [account for account in config.get("USERS", []) if account.get("access_key")]
    if not accounts:
        raise ValueError("未找到有效的 B 站 access_key")
    await asyncio.gather(*(run_account(account, settings) for account in accounts))


if __name__ == "__main__":
    asyncio.run(main())
