# Room Protocol (Phase 1–2)

此文件描述目前 `Room` 已實作的事件契約與回傳格式。  
程式碼來源：`core/room.py`、`core/states.py`、`core/events.py`、`core/ports.py`。

## 1) 基本原則

- 單一入口：`Room.handle(event, **kwargs)`
- **輸入事件**（Client → Server）：字串名稱，定義於 `core/events.py` 的 `InboundEvent`
- **輸出事件**（Server → Client）：JSON 物件，至少包含 `type`；錯誤另含 `code` + `message`
- 輸入事件是否合法由目前 state 決定（State Pattern）

## 2) 事件總覽

### Client → Server（輸入）

| 事件 | 定義位置 | 說明 |
|---|---|---|
| `join` | `core.events.JOIN` | 玩家加入房間 |
| `start` | `core.events.START` | 房主開始遊戲 |
| `submit` | `core.events.SUBMIT` | 提交程式碼 |
| `violation` | `core.events.VIOLATION` | 記錄防作弊違規（分頁失焦等） |

### Server → Client（輸出）

| `type` | 觸發時機 |
|---|---|
| `error` | 參數錯誤、狀態不允許、房間規則拒絕 |
| `player:joined` | 玩家成功加入 |
| `state:changed` | 房間階段切換 |
| `game:started` | 遊戲開始，附題目與計時秒數 |
| `submission:received` | 收到某位玩家的提交 |
| `violation:recorded` | 違規次數更新 |
| `game:result` | 評分結束，附各玩家分數 |

## 3) 狀態與允許的輸入事件

| State | 允許事件 | 備註 |
|---|---|---|
| `LobbyState` | `join` | 玩家加入房間 |
| `ReadyState` | `start` | 僅房主可開始（房主 = `players[0]`） |
| `PlayingState` | `submit`, `violation` | 提交與違規記錄 |
| `JudgingState` | 無 | 一律回 `INVALID_EVENT` |
| `ResultState` | 無 | 一律回 `INVALID_EVENT` |

## 4) Client -> Server 事件（目前已定義）

### `join`

- payload:
  - `player: str`（必填）

行為：
- `LobbyState` 允許
- 缺 `player` -> error `MISSING_PARAM`
- 重複加入 -> error `DUPLICATE_PLAYER`
- 房間滿員 -> error `ROOM_FULL`
- 加入成功 -> `player:joined`
- 人數達 `max_players` -> `state:changed`（`ReadyState`）

### `start`

- payload:
  - `player: str`（必填）

行為：
- `ReadyState` 允許
- 缺 `player` -> error `MISSING_PARAM`
- 非房主 -> error `NOT_HOST`
- 房主 -> 呼叫 `start_game()`（含出題、`state:changed`、`game:started`、啟動計時器）

### `submit`

- payload:
  - `player: str`（必填）
  - `code: str`（必填）

行為：
- `PlayingState` 允許
- 缺參數 -> error `MISSING_PARAM`
- 成功 -> `submission:received`
- 若所有玩家皆提交 -> 自動觸發結算（`state:changed` → `JudgingState` → `ResultState` → `game:result`）

### `violation`

- payload:
  - `player: str`（系統事件，正常必填）

行為：
- `PlayingState` 允許
- 缺 `player` -> 靜默略過（不送 error）
- 成功 -> 違規次數 +1，送出 `violation:recorded`

## 5) Server -> Client 事件格式

### 通用錯誤事件

```json
{
  "type": "error",
  "code": "MISSING_PARAM",
  "message": "缺少 player 參數"
}
```

### `player:joined`

```json
{
  "type": "player:joined",
  "player": "alice",
  "players": ["alice", "bob"]
}
```

### `state:changed`

```json
{
  "type": "state:changed",
  "state": "ReadyState"
}
```

`state` 值為 Python state class 名稱：`LobbyState`、`ReadyState`、`PlayingState`、`JudgingState`、`ResultState`。

### `game:started`

```json
{
  "type": "game:started",
  "question": {
    "id": 1,
    "title": "Two Sum",
    "difficulty": "easy",
    "description": "Return indices of two numbers that add up to target.",
    "examples": [
      {
        "input": "nums = [2,7,11,15], target = 9",
        "output": "[0,1]",
        "explanation": "Because nums[0] + nums[1] = 9."
      }
    ],
    "constraints": ["2 <= len(nums) <= 10^4"],
    "starter_code": {
      "python": "def solve(nums, target):\n    pass",
      "js": "function solve(nums, target) {\n  return [];\n}"
    }
  },
  "duration_seconds": 300
}
```

`question` 欄位 contract（對齊 `core.ports.QuestionPayload`）：

| key | type | 說明 |
|---|---|---|
| `id` | int | 題目唯一 ID |
| `title` | str | 題目標題 |
| `difficulty` | str | `easy` \| `medium` \| `hard` |
| `description` | str | 題目描述（評分主要依據） |
| `examples` | list | 每筆含 `input`、`output`、`explanation`（可為 null） |
| `constraints` | list[str] | 題目限制條件 |
| `starter_code` | dict[str, str] | 語言 → 初始程式碼（如 `python`、`js`） |

### `submission:received`

```json
{
  "type": "submission:received",
  "player": "alice"
}
```

### `violation:recorded`

```json
{
  "type": "violation:recorded",
  "player": "alice",
  "count": 1
}
```

### `game:result`

```json
{
  "type": "game:result",
  "results": {
    "alice": {
      "score": 8.0,
      "penalty": 5,
      "final_score": 3.0
    },
    "bob": {
      "score": 0.0,
      "penalty": 0,
      "final_score": 0.0
    }
  }
}
```

每位玩家的結果欄位：

| key | type | 說明 |
|---|---|---|
| `score` | float | AI 原始分數（0–10，由 `IJudgeService` 回傳） |
| `penalty` | int | 違規扣分總額（`violations × violation_penalty`） |
| `final_score` | float | `max(score - penalty, 0)` |

> `feedback` 尚未納入 `game:result`；若 judge adapter 有回傳，目前僅用於評分，不會廣播給客戶端。

## 6) 錯誤碼清單（目前）

| code | 說明 |
|---|---|
| `INVALID_EVENT` | 當前 state 不允許該輸入事件 |
| `MISSING_PARAM` | 事件缺必要參數 |
| `NOT_HOST` | 非房主嘗試 `start` |
| `DUPLICATE_PLAYER` | 玩家重複加入 |
| `ROOM_FULL` | 房間人數已達上限 |

## 7) Pending（之後補齊）

以下會在後續 Phase 補齊：

- 輸出事件 TypedDict union（`OutboundEvent`）與 runtime 驗證
- WebSocket endpoint URL 與 handshake 細節（Phase 4）
- REST 與 WS 欄位共用 schema（Phase 3/4）
- `game:result` 納入 `feedback` 廣播
- reconnect / replay / 斷線恢復策略（Phase 6）
