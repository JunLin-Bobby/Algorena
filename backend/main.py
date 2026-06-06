from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import get_settings
from wiring import build_app_dependencies


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.deps = build_app_dependencies(get_settings())
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}