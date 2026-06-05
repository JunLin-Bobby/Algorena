# Algorena

FastAPI backend for Algorena.

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

### 2. Run the API

```powershell
uv run uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Interactive API docs are at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Project layout

```text
Algorena/
├── README.md
└── backend/
    ├── main.py
    └── pyproject.toml
```
