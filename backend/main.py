import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import get_settings
from db import create_engine, create_session_factory, init_db, seed_questions
from wiring import build_app_dependencies

DEBUG_STARTUP = os.environ.get("DEBUG_STARTUP") == "1"


def _trace(step: str) -> None:
    if DEBUG_STARTUP:
        print(f"[startup] {step}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _trace("1/5 create_engine")
    engine = create_engine(settings.database_url)
    _trace("2/5 init_db (alembic)")
    await init_db(engine)
    _trace("3/5 create_session_factory")
    session_factory = create_session_factory(engine)
    _trace("4/5 seed_questions")
    await seed_questions(session_factory)
    _trace("5/5 build_app_dependencies")

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.deps = build_app_dependencies(settings)
    _trace("ready")

    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}