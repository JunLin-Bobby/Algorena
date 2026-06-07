# Algorena

FastAPI backend for Algorena — competitive coding rooms over WebSocket, with a SQLite question bank.

## Prerequisites

- [Python](https://www.python.org/) 3.11+
- [uv](https://docs.astral.sh/uv/) (Python package and project manager)

## Quick start (Windows)

From the repo root:

### 1. Install

```powershell
cd backend
uv sync
```

`uv sync` 會依 [`backend/pyproject.toml`](backend/pyproject.toml) 與 `uv.lock` 建立/更新 `.venv` 並安裝所有依賴，不需要再手動 `uv add`。

若要啟用虛擬環境（可選，直接用 `uv run` 則不必）：

```powershell
.\.venv\Scripts\Activate.ps1
```

> **Note:** 新增套件時用 `uv add <package>`，它會寫入 `pyproject.toml` 並更新 lock；之後其他人仍只需 `uv sync`。

### 2. Environment (optional)

```powershell
copy .env.example .env
```

未設定 `DATABASE_URL` 時，預設使用 `backend/algorena.db`。Schema 由 **Alembic** 管理，不是啟動 API 時自動建表。

### 3. Database migrations

**第一次** clone、或 pull 到有新 migration 的版本後，在 `backend/` 執行：

```powershell
uv run alembic upgrade head
```

這會建立／更新 `questions` 表（預設寫入 `algorena.db`）。日常只改應用程式、沒動 `alembic/versions/` 時，**不必**每次重跑。

常用指令：

```powershell
uv run alembic current          # 目前 migration 版本
uv run alembic history          # 版本歷史
uv run alembic downgrade -1     # 還原上一版（開發用）
```

> **Note:** `uv run uvicorn ...` **不會**自動跑 migration；需手動 `alembic upgrade head`（或之後在 app startup 接線）。

### 4. Run the API

```powershell
uv run uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Interactive API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 5. Tests

```powershell
uv run pytest
```

## Project layout

```text
Algorena/
├── README.md
└── backend/
    ├── alembic/              # Alembic migrations
    ├── alembic.ini
    ├── core/                 # Room state machine, ports
    ├── adapters/             # Judge, question, WebSocket notify
    ├── db/                   # Session, models, migrate helpers
    ├── docs/                 # Protocol & phase steps
    ├── main.py
    ├── config.py
    ├── wiring.py
    └── pyproject.toml
```

More detail: [`backend/docs/protocol.md`](backend/docs/protocol.md), [`backend/docs/phase3_steps.md`](backend/docs/phase3_steps.md).
