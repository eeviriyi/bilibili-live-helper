# Fans Medal Helper

A personal Bilibili live-stream task runner. It polls the fan-medal panel and
starts work only when a streamer with one of your medals is live.

For each streamer, once per Asia/Shanghai calendar day, the runner:

1. Reports one 300-click like.
2. Sends live heartbeats for the configured duration.
3. Sends `[花]` or `[比心]` ten times by default, with a three-minute interval.

The process has no HTTP server and exposes no port.

When `ntfy.endpoint` is configured, task completion is sent to that topic.
Notification delivery failures are logged and never interrupt a stream task.

## Configuration

Create a private `users.yaml` from `users.example.yaml`. The file contains an
account credential and must never be committed or shared.

`include_uids` limits tasks to the listed streamer UIDs. An empty list includes
all medal holders. `exclude_uids` is applied only when `include_uids` is empty.

## Run Locally

```bash
uv sync
uv run python -m fans_medal_helper
```

## Run With Docker

```bash
docker build -t fans-medal-helper .
docker run -d --name fans-medal-helper \
  --restart unless-stopped \
  -v "$PWD/users.yaml:/app/users.yaml:ro" \
  fans-medal-helper
```

## Behavior And Limits

- Live state is refreshed every `poll_interval_seconds`.
- A transient API failure is retried three times with exponential backoff; a
  failed poll is retried at the next polling interval.
- Stream tasks are capped by `max_concurrent_streams`.
- The per-day task record is in memory. Restarting the process may repeat a
  task for a streamer already handled that day.
- Bilibili API behavior and anti-abuse policies can change. Use conservative
  intervals and monitor logs after changing task volume.

## Development

```bash
uv run pytest
uv run ruff check .
```
