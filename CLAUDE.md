# 專案指引

**語言：請使用繁體中文回應使用者。**

<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## Infrastructure

### Application

- Port: `8089` (APP_PORT)
- Health check: `http://localhost:8089/health`
- Start: `./scripts/start.sh` or `uv run python main.py`

### Database

- Container name: `jaba-ai-postgres`
- Default credentials: `jaba_ai` / `jaba_ai_secret`
- Database name: `jaba_ai`
- Port: `5433` (mapped to container's 5432)

### Super Admin（超級管理員）

- 帳密請參考 `@/.env` 中的 `INIT_ADMIN_USERNAME` / `INIT_ADMIN_PASSWORD`
- 後台網址：`http://localhost:8089/admin.html`

Access database via docker:
```bash
docker exec jaba-ai-postgres psql -U jaba_ai -d jaba_ai -c "YOUR SQL HERE"
```

### Migrations

Run migrations with uv:
```bash
uv run alembic upgrade head
uv run alembic current
```