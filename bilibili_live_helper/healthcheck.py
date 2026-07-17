import json
import os
import time
from pathlib import Path

from .config import load_settings
from .state import read_state


def check_health(
    config_path: Path, state_path: Path, *, now: float | None = None
) -> tuple[bool, str]:
    try:
        settings = load_settings(config_path)
        state = read_state(state_path)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        return False, f"unreadable configuration or state: {type(error).__name__}"
    if state.last_successful_poll_at is None:
        return False, "no successful live-state poll recorded"
    maximum_age = max(300, settings.poll_interval_seconds * 3)
    age = (time.time() if now is None else now) - state.last_successful_poll_at
    if age < 0 or age > maximum_age:
        return False, f"last successful live-state poll is {int(age)} seconds old"
    return True, "ok"


def main() -> None:
    config_path = Path(os.environ.get("BILIBILI_LIVE_HELPER_CONFIG", "users.yaml"))
    state_path = Path(os.environ.get("BILIBILI_LIVE_HELPER_STATE", "data/state.json"))
    healthy, message = check_health(config_path, state_path)
    print(message)
    raise SystemExit(0 if healthy else 1)


if __name__ == "__main__":
    main()
