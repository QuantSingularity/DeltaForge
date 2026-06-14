# DeltaForge — Scripts

Convenience entry points. All scripts resolve the project root themselves, so
they work from any directory. Python scripts set `PYTHONPATH=code` for you.

| Script              | Purpose                                                                          |
| ------------------- | -------------------------------------------------------------------------------- |
| `setup.sh`          | One-time setup: install Python + API deps, create config, install frontend deps. |
| `run_sandbox.sh`    | Run the bot in sandbox (paper trading) mode.                                     |
| `run_bot.sh`        | Run the live trading bot. Set `DELTAFORGE_EXCHANGE` to override the exchange.    |
| `run_backtest.sh`   | Run a walk-forward backtest across configured pairs.                             |
| `retrain_ml.sh`     | Retrain the ML signal scorer from recorded trade outcomes.                       |
| `run_dashboard.sh`  | Serve the dashboard API (and the built frontend if present) on port 8000.        |
| `dev.sh`            | Full-stack dev: FastAPI (`:8000`) + Vite dashboard (`:5173`) with hot reload.    |
| `build_frontend.sh` | Install and build the dashboard into `web-frontend/dist`.                        |
| `test.sh`           | Run the full test suite (404 tests). Extra args pass through to pytest.          |
| `lint.sh`           | Check Python (black + autoflake) and frontend lint. Pass `--fix` to auto-format. |
| `docker_up.sh`      | Build and start the full stack in Docker (dashboard `:8080`, API `:8000`).       |
| `docker_down.sh`    | Stop and remove the Docker stack.                                                |

## Typical flows

```bash
./scripts/setup.sh                 # first time
./scripts/dev.sh                   # develop with hot reload
./scripts/test.sh                  # before committing
./scripts/run_sandbox.sh           # paper-trade headless
./scripts/docker_up.sh             # full stack in containers
```

## Environment variables

| Variable              | Used by                         | Default      |
| --------------------- | ------------------------------- | ------------ |
| `DELTAFORGE_EXCHANGE` | `run_bot.sh`, `run_backtest.sh` | config value |
| `DELTAFORGE_PORT`     | `run_dashboard.sh`, `dev.sh`    | `8000`       |
