"""Algorena 啟動流程除錯腳本（開發用，非正式部署路徑）。

用途
----
逐步執行 main.py lifespan 的每個階段，並記錄耗時與結果，用來定位
「uvicorn 卡住 / 無 Application startup complete / HTTP 無回應」等
啟動問題。Phase 3 曾用此腳本找出 Alembic fileConfig 與 uvicorn
logging 衝突導致的死鎖。

執行步驟（預設）
  0. 環境檢查（cwd、algorena.db、port 8000）
  1. 載入 questions.yaml
  2. 同步 Alembic upgrade_head
  3. await init_db（to_thread）
  4. await seed_questions
  5. 完整 lifespan（asyncio 風格）
  6. FastAPI TestClient GET /
  7. （可選）spawn uvicorn 子行程，等待 startup complete

使用方法（在 backend/ 目錄下）
----
    uv run python scripts/debug_startup.py
    uv run python scripts/debug_startup.py --with-uvicorn
    uv run python scripts/debug_startup.py --with-uvicorn --with-reload

輸出
----
  - 終端機即時 trace
  - 完整紀錄寫入 backend/debug_startup.log（每次執行會覆寫舊 log）

何時需要
----
  - 改動 lifespan、seed、Alembic 後懷疑啟動異常
  - 本機 port / DB 鎖定、殭屍 process 等環境問題排查

何時不需要
----
  - 日常開發直接用 uv run python -m uvicorn main:app --reload
  - CI / 正式驗收請用 pytest（tests/test_main_lifespan.py 等）
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
LOG_PATH = BACKEND_DIR / "debug_startup.log"
sys.path.insert(0, str(BACKEND_DIR))


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(message: str) -> None:
    line = f"[{_ts()}] [pid={os.getpid()}] {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def log_section(title: str) -> None:
    log("")
    log(f"=== {title} ===")


def run_step(name: str, fn) -> bool:
    log(f"START {name}")
    started = time.perf_counter()
    try:
        fn()
        elapsed = time.perf_counter() - started
        log(f"OK    {name} ({elapsed:.3f}s)")
        return True
    except Exception as exc:
        elapsed = time.perf_counter() - started
        log(f"FAIL  {name} ({elapsed:.3f}s): {exc!r}")
        log(traceback.format_exc())
        return False


async def run_async_step(name: str, coro_fn) -> bool:
    log(f"START {name}")
    started = time.perf_counter()
    try:
        await coro_fn()
        elapsed = time.perf_counter() - started
        log(f"OK    {name} ({elapsed:.3f}s)")
        return True
    except Exception as exc:
        elapsed = time.perf_counter() - started
        log(f"FAIL  {name} ({elapsed:.3f}s): {exc!r}")
        log(traceback.format_exc())
        return False


def check_environment() -> None:
    log_section("0. Environment")
    log(f"cwd={Path.cwd()}")
    log(f"python={sys.executable}")

    db_path = BACKEND_DIR / "algorena.db"
    log(f"algorena.db exists={db_path.exists()} size={db_path.stat().st_size if db_path.exists() else 0}")

    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(db_path) + suffix)
        log(f"{sidecar.name} exists={sidecar.exists()}")

    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
        )
        port_lines = [
            line.strip()
            for line in result.stdout.splitlines()
            if ":8000" in line
        ]
        if port_lines:
            log("port 8000 listeners:")
            for line in port_lines:
                log(f"  {line}")
        else:
            log("port 8000: free")
    except OSError as exc:
        log(f"netstat skipped: {exc!r}")


def check_imports_and_yaml() -> None:
    log_section("1. YAML load")
    from db.seed import DEFAULT_QUESTIONS_PATH, load_questions_from_yaml

    log(f"questions.yaml={DEFAULT_QUESTIONS_PATH}")
    questions = load_questions_from_yaml(DEFAULT_QUESTIONS_PATH)
    log(f"loaded {len(questions)} questions; ids={ [q['id'] for q in questions[:5]] }...")


def check_sync_migration() -> None:
    log_section("2. Sync Alembic upgrade_head")
    from config import get_settings
    from db.migrate import upgrade_head

    settings = get_settings()
    log(f"database_url={settings.database_url}")
    upgrade_head(settings.database_url)


async def check_init_db() -> None:
    log_section("3. await init_db (to_thread upgrade)")
    from config import get_settings
    from db import create_engine, init_db

    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        await init_db(engine)
    finally:
        await engine.dispose()


async def check_seed() -> None:
    log_section("4. await seed_questions")
    from config import get_settings
    from db import create_engine, create_session_factory, init_db, seed_questions
    from db.repositories.question_repository import QuestionRepository

    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    try:
        await init_db(engine)
        await seed_questions(session_factory)
        async with session_factory() as session:
            repo = QuestionRepository(session)
            count = len(await repo.list_all())
        log(f"questions in DB after seed: {count}")
    finally:
        await engine.dispose()


async def check_full_lifespan() -> None:
    log_section("5. Full lifespan (asyncio.run style)")
    from main import app, lifespan

    async with lifespan(app):
        log("inside lifespan yield")


def check_testclient() -> None:
    log_section("6. FastAPI TestClient")
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        response = client.get("/")
        log(f"GET / -> {response.status_code} {response.json()}")


def check_uvicorn(timeout_seconds: int, reload: bool) -> None:
    log_section(f"7. Uvicorn subprocess (reload={reload}, timeout={timeout_seconds}s)")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    if reload:
        cmd.append("--reload")

    log(f"cmd={' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    started = time.perf_counter()
    saw_startup_complete = False
    output_lines: list[str] = []

    try:
        assert process.stdout is not None
        while time.perf_counter() - started < timeout_seconds:
            line = process.stdout.readline()
            if line:
                line = line.rstrip()
                output_lines.append(line)
                log(f"  uvicorn | {line}")
                if "Application startup complete" in line:
                    saw_startup_complete = True
                    break
            elif process.poll() is not None:
                break
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

    elapsed = time.perf_counter() - started
    if saw_startup_complete:
        log(f"OK    uvicorn startup complete ({elapsed:.3f}s)")
    else:
        log(f"HANG  uvicorn did not finish startup within {timeout_seconds}s ({elapsed:.3f}s)")
        if output_lines:
            log("last uvicorn lines:")
            for line in output_lines[-5:]:
                log(f"  > {line}")


async def main(with_uvicorn: bool, with_reload: bool) -> None:
    if LOG_PATH.exists():
        LOG_PATH.unlink()

    log_section("Algorena startup debug")
    check_environment()

    steps = [
        ("yaml", check_imports_and_yaml),
        ("sync migrate", check_sync_migration),
    ]
    for name, fn in steps:
        if not run_step(name, fn):
            log(f"STOP: failed at {name}")
            return

    async_steps = [
        ("init_db", check_init_db),
        ("seed", check_seed),
        ("lifespan", check_full_lifespan),
    ]
    for name, coro in async_steps:
        if not await run_async_step(name, coro):
            log(f"STOP: failed at {name}")
            return

    if not run_step("testclient", check_testclient):
        return

    if with_uvicorn:
        check_uvicorn(timeout_seconds=20, reload=with_reload)

    log_section("Done")
    log(f"Full trace written to {LOG_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug Algorena startup steps")
    parser.add_argument(
        "--with-uvicorn",
        action="store_true",
        help="Also spawn uvicorn and watch for 'Application startup complete'",
    )
    parser.add_argument(
        "--with-reload",
        action="store_true",
        help="Use uvicorn --reload (only with --with-uvicorn)",
    )
    args = parser.parse_args()
    asyncio.run(main(with_uvicorn=args.with_uvicorn, with_reload=args.with_reload))
