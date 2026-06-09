"""最小 FastAPI + uvicorn 煙霧測試（開發用，非正式 app）。

用途
----
提供一個不含 DB / Alembic / seed 的最小 app，用來確認本機
uvicorn 與 FastAPI lifespan 是否正常。若此腳本能啟動而 main:app
不能，問題在 Algorena 的 lifespan 邏輯；若兩者都不行，則偏向
環境（port 占用、venv、uvicorn 安裝）問題。

使用方法（在 backend/ 目錄下）
----
    uv run python scripts/minimal_uvicorn_test.py

預期輸出包含：
    Application startup complete.
    Uvicorn running on http://127.0.0.1:8000

瀏覽器或 curl 打 GET / 應回 {"ok": true}。Ctrl+C 結束。

何時需要
----
  - 懷疑 uvicorn 本身或 Windows 環境有問題時，作為對照組
  - 排查啟動 hang 的第一步（先跑此腳本，再跑 debug_startup.py）

何時不需要
----
  - 日常開發與驗收請用 main:app 與 pytest
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("minimal ready", flush=True)
    yield
    print("minimal shutdown", flush=True)


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
