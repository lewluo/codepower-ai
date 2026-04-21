# JoyInside Skill Gateway

This gateway exposes the existing CodePower dispatcher tools as a JoyInside custom skill API.

Local run:

```bash
JOYINSIDE_SERVICE_TOKEN=dev-token PORT=9100 \
  dispatcher/.venv/bin/python joyinside_gateway/server.py
```

Local test:

```bash
curl -N -X POST 'http://127.0.0.1:9100/joyinside/skill?tool=list_agents' \
  -H 'Authorization: Bearer dev-token' \
  -H 'Content-Type: application/json' \
  -d '{"parameters":{"input":"列出所有可用 agent","session_id":"local","bot_id":"local"}}'
```

JoyInside platform configuration:

- API URL: `https://<your-public-domain>/joyinside/skill?tool=list_agents`
- Auth: Service Token
- Token location: Header
- Token header/value: `Authorization: Bearer <your token>`
- Response mode: streaming SSE events: `Message` followed by `Done`

Create separate JoyInside custom skills by registering the same path with different `tool` query values:

- `tool=list_agents`
- `tool=read_daily_report`
- `tool=query_agent_status`
- `tool=dispatch_agent`

