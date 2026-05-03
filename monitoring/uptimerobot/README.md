# UptimeRobot Configuration

This directory contains templates for alerting and uptime checks for the public demo
surface.

## Monitors (6 total)

Create these six monitors in UptimeRobot against the deployed domain or tunnel host:

1. `vCAS API Health` -> `GET /health`
2. `vCAS Alert Feed` -> `GET /api/alerts`
3. `vCAS Audit Chain` -> `GET /api/audit-chain-verify`
4. `vCAS Metrics` -> `GET /metrics`
5. `vCAS Demo UI` -> `GET /demo`
6. `vCAS Dashboard` -> `GET /` on dashboard port/path

Use HTTP/HTTPS monitors with 30s interval and 120s timeout.

`monitoring/uptimerobot/monitors.template.json` provides a shell-style variable
template you can pass through `envsubst`.

## Telegram alerting

Configure at least one Telegram notification contact in UptimeRobot with:

- bot token from Telegram (`BOT_TOKEN`)
- chat id for the destination channel or group

`monitoring/uptimerobot/telegram.template.json` contains a payload example.

## Apply flow

```bash
export UPTIME_ROBOT_API_KEY=...
export VCAS_BASE_URL=https://vcas.example.com
envsubst < monitoring/uptimerobot/monitors.template.json > /tmp/monitors.json
curl -X POST "https://api.uptimerobot.com/v2/newMonitor" \
  -H "Content-Type: application/json" \
  --data @/tmp/monitors.json
```

Attach the Telegram contact ID returned by UptimeRobot to each monitor for outage
notifications and optionally wire a second contact for critical alerts.
