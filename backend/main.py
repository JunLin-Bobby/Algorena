from fastapi import FastAPI

# Phase 4: from config import get_settings
# settings = get_settings()
# Room(..., max_players=settings.max_players,
#      game_duration_seconds=settings.game_duration_seconds,
#      violation_penalty=settings.violation_penalty)

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}