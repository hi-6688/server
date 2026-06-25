# AGENTS.md

Compact guidance for AI coding agents working in this repo. Repo root is the git repo `github.com/hi-6688/server`.

## Repo layout — what is and isn't the main project

The active project is the Discord bot. Several sibling directories are **vendored third-party projects** with their own instruction files — do not modify them as if they were bot code unless explicitly asked.

- `discord_bot/` — **the main project**: Python Discord bot (HiHi AI + Conch + Test personas). Entry point `main.py`.
- `pokemon_bot/` — Node/TS Discord Pokémon battle bot (actively developed; most recent commits). See its section below.
- `hermes-agent-admin/`, `hihi/` — vendored copies of the `hermes-agent` CLI; each has its own `AGENTS.md`. `hihi/` is injected into `sys.path` by `discord_bot/main.py`.
- `honcho/` — vendored Honcho project; has its own `CLAUDE.md` + Alembic migrations.
- `teambuilder_client/` — vendored Pokémon Showdown teambuilder (Node + PHP/composer).
- `web_interface/` — FastAPI web panel; **deprecated/disabled** per README (resource constraints). Files remain but it is not deployed.
- `scratch/` — ad-hoc Python utility scripts.
- `scripts/` — operational scripts: `db/`, `deploy/`, `maintenance/`, `migration/`, `setup/`, `sync/`, `tests/`.
- `configs/systemd/` — systemd unit files for the three bot personas + `mc_agent`.
- `docs/` — `TECHNICAL_SPEC.md` is the SSOT for Pydantic schemas/vector specs; `ai_rules/workflow.md` is the workflow rule file (imported by `GEMINI.md`).

## discord_bot architecture

- **Split persona via `BOT_MODE` env** (`HIHI` | `CONCH` | `TEST`): selects the Discord token and which cogs load. Map defined in `main.py::setup_hook`. `ALL` (default) loads everything except `inactive.*`.
- Cogs live in `cogs/<group>/`: `common/status.py`, `hihi/ai_chat.py` (the AI brain), `conch/conch_game.py`, `inactive/{minecraft,terraria,vm_admin}.py`.
- `agent/` is the newer ADK-style core (`orchestrator.py`, `memory.py`, `scheduler.py`, `schemas.py`, `telemetry.py`, `tools.py`). Shared utils live in `hihi_utils/` (`emoji_service`, `gcp_manager`, `quota_manager`, `scheduler_tools`, `bds_updater`).
- ⚠️ The README's "Active File Architecture" diagram is **stale**: it lists `discord_bot/utils/` (actual: `hihi_utils/`) and omits `agent/`, `cli.py`, `.adk/`. Trust the filesystem, not that diagram.
- `main.py` hardcodes `sys.path.insert(0, "/home/hi6688/servers/hihi")` and strips `honcho/src` from `sys.path`. Update if the vendored `hihi/` moves.
- `.env` is loaded from the **repo root** (`servers/.env`), one level up from `main.py`. Keys: `BOT_MODE`, `DISCORD_TOKEN`/`CONCH_TOKEN`/`TEST_TOKEN`, `DATABASE_URL`, `GEMINI_API_KEY`, `AI_MODEL_NAME`. Template: `.env.example`.
- Tech stack: `google-genai==2.8.0`, model `gemini-3.1-flash-lite`, embedding `gemini-embedding-2` (768-dim, L2-normalized), Azure PostgreSQL + `pgvector` (HNSW), hybrid retrieval (cosine + BM25 + RRF).

## Commands

**No repo-wide linter, formatter, typecheck, or test runner is configured** (no ruff/flake8/pre-commit/pytest at root; no root `package.json`). Verify by running scripts directly — do not assume `npm test` / `pytest` / `ruff` works.

Python bot (from `discord_bot/`, using its own `.venv`):
- Setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Run bot: `.venv/bin/python3 main.py` (needs root `.env` + `BOT_MODE`)
- Local CLI chat (no Discord): `.venv/bin/python3 cli.py` (see `scripts/setup/hihi.sh`)
- Cog syntax check: `python scripts/tests/test_cog_syntax.py`
- DB / maintenance: standalone scripts in `scripts/db/`, `scripts/maintenance/` (each needs `.env` / DB access)

pokemon_bot (Node/TS, ESM, strict `tsc`):
- `npm run dev` — run via tsx
- `npm run build` — `tsc` → `dist/`
- `npm run deploy` — register slash commands (needs token)
- `npm run test-canvas` — canvas rendering test

## Deployment gotchas

- Bots run as **systemd** services (`configs/systemd/{discord_bot,conch_bot,test_bot}.service`).
- ⚠️ **Path/user mismatch:** systemd units and `scripts/setup/hihi.sh` target production at `User=terraria`, `WorkingDirectory=/home/terraria/servers/...`. This dev box is `/home/hi6688/servers/`. Several scripts (e.g. `scripts/tests/test_cog_syntax.py`) also hardcode `/home/terraria/servers/...` and will need path adjustment to run locally. Meanwhile `discord_bot/main.py` hardcodes the `hi6688` path. Do not assume systemd paths exist on this box.
- `docker-compose.yml` exists but the web panel is commented out. README states Docker is **not used** — bots run natively under systemd (target RAM < 150MB).
- Restart a persona: `sudo systemctl restart discord_bot.service` (or `conch_bot`/`test_bot`). Tail logs: `journalctl -u discord_bot.service -f`.

## Workflow conventions

- **After every code/config change, automatically update `CHANGELOG.md` and `ROADMAP.md`** — do not wait to be asked. This is the binding rule in `docs/ai_rules/workflow.md` (imported by `GEMINI.md`).
- Commit style: conventional-ish prefixes, messages in Chinese (e.g. `feat(ui): ...`, `修復: ...`, `優化: ...`).
- Active branch: `dev`. `main` is the release branch.
- CI (`.github/workflows/`) is **Gemini-agent-driven** (triage, review, plan-execute) — not standard test/lint. No automated code-quality gates.

## AI content rules (when editing bot memory/persona code)

From `docs/ai_rules/workflow.md`: emotions must **emerge** from conversation context — never hardcode mood/emotion in the DB. Emoji, custom emoji, and kaomoji are high-weight anchors for user intent and bonding; give them strong weight in memory retrieval and response logic.
