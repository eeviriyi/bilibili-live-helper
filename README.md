# Bilibili Live Helper

A single-account Bilibili live-stream task runner for a private whitelist. It
has no HTTP server and exposes no port.

## Behavior

Every `poll_interval_seconds`, one public batch request resolves the configured
UIDs into current room metadata and live status. The fan-medal panel is not used
for discovery or validation; `include_uids` is the source of truth.

When a whitelisted streamer is live, the runner independently starts:

- ten 30-click like reports, with the configured interval;
- ten Danmaku messages (`[花]` or `[比心]`), with a three-minute interval;
- watching heartbeats when the UID is in `watch_uids`.

Only one watching task runs at a time. `watch_uids` is ordered: the first live,
unfinished UID gets the slot whenever it becomes available. A live-state poll
stops the current watching task after the streamer goes offline. `watch_minutes`
is an exact duration target: the runner waits and accounts in seconds until it
reaches `watch_minutes * 60`. Changing the heartbeat interval changes the number
of requests, not the total watch duration.

Like sequences for different rooms advance independently. Individual Bilibili
requests are still serialized per account, but one room never holds a lock while
waiting for its next like interval.

Likes and Danmaku do not wait for watching. After both finish, ntfy receives:

```text
Title: 「Streamer name」 Automatic task completed
Body:  UID: 123456789
       300 live likes and 10 Danmaku sent.
```

Watching is reported once at midnight in `Asia/Shanghai`.

## State And Recovery

State is written atomically before every side-effecting request and again after
each confirmed response. A restart resumes only unfinished work for the current
day. If a request times out after it may have reached Bilibili, that attempt is
recorded as uncertain and is not repeated. Completion notifications distinguish
confirmed work from uncertain attempts. At midnight, running work is stopped
before the state changes to the new day.

ntfy messages first enter the same persistent state file. Failed deliveries use
exponential backoff and remain there until accepted. Custom sequence IDs contain
only letters, numbers, underscores, and hyphens.

The current version-1 state reader is backward compatible with files written
before attempt and second-based watch tracking were added. An invalid or
unsupported state file is moved aside as `state.json.corrupt-TIMESTAMP` so it
cannot permanently block polling.

## Configuration

Create `users.yaml` from [users.example.yaml](users.example.yaml). The schema is
strict and supports exactly one account:

```yaml
access_key: REPLACE_ME
include_uids:
  - 123456789
watch_uids:
  - 123456789
```

`include_uids` must not be empty. Every `watch_uids` entry must also be in
`include_uids`. Duplicate YAML keys, duplicate UIDs, and unknown fields are
rejected. Like reports are limited to at most 300 clicks per request.

The runner treats a Bilibili `code: 0` response as success. It deliberately does
not add extra intimacy or like-count verification requests.

## Run Locally

Python 3.14 and uv are required.

```bash
uv sync
uv run python -m bilibili_live_helper
```

Local state defaults to `data/state.json`. Paths can be overridden for one run:

```bash
BILIBILI_LIVE_HELPER_CONFIG=/path/to/users.yaml \
BILIBILI_LIVE_HELPER_STATE=/path/to/state.json \
uv run python -m bilibili_live_helper
```

## Run With Docker

```bash
mkdir -p data
docker compose up -d --build
docker compose ps
```

The repository [compose.yaml](compose.yaml) exposes no port. It adds a
state-freshness health check, a 30-second graceful-stop window, bounded Docker
log rotation, a read-only root filesystem, and a writable `/data` mount. The
image also carries the same health check when it is run without Compose.

## API Design

- Live discovery uses `Room/get_status_info_by_uids`, one request for the full
  whitelist. It returns UID, room ID, name, area, title, and live status.
- Public room and web Danmaku conventions were checked against
  [`bilibili-api-python` 17.4.2](https://pypi.org/project/bilibili-api-python/).
  That library does not expose the app-signed live-like or account watch-credit
  endpoints used here, so it is a reference rather than a runtime dependency.
- Account actions retain the app `access_key` signing path used by the working
  like and Danmaku endpoints.
- Watching uses the authenticated app `mobileHeartBeat`. The anonymous web
  heartbeat used for live WebSocket connections is not an account watch-credit
  substitute.
- All individual Bilibili HTTP requests are serialized per account and separated
  by at least `api_interval_seconds`. GET requests may retry. A definitive API
  rejection leaves the attempt eligible for a later poll; an ambiguous POST
  result consumes its durable reservation and is never sent again.

## Development

```bash
uv run pytest -p no:cacheprovider
uv run ruff check . --no-cache
uv lock --check
```

GitHub Actions runs these checks and builds the Docker image for every push and
pull request to `master`.
