# Room Protocol (Phase 1)

此文件描述目前 `Room` 已實作的事件契約與回傳格式。  
目前涵蓋 Step 1~3（Lobby/Ready/Playing/Judging/Result 的核心事件）；未完成部分會標記為 pending。

## 1) 基本原則

- 單一入口：`Room.handle(event, **kwargs)`
- 事件是否合法由目前 state 決定（State Pattern）
- 後端回傳統一事件格式（至少包含 `type`；錯誤包含 `code` + `message`）

## 2) 狀態與允許事件

| State | 允許事件 | 備註 |
|---|---|---|
| `LobbyState` | `join` | 玩家加入房間 |
| `ReadyState` | `start` | 僅房主可開始（房主 = `players[0]`） |
| `PlayingState` | `submit`, `violation` | Phase 1 Step 2 才會完整生效 |
| `JudgingState` | 無 | 目前一律拒絕 |
| `ResultState` | 無 | 目前一律拒絕 |

## 3) Client -> Server 事件（目前已定義）

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
- 房主 -> 呼叫 `start_game()`

### `submit`

- payload:
  - `player: str`（必填）
  - `code: str`（必填）

行為：
- `PlayingState` 允許
- 缺參數 -> error `MISSING_PARAM`
- 成功 -> `submission:received`
- 若雙方都提交 -> 自動觸發結算（`game:result`）

### `violation`

- payload:
  - `player: str`（系統事件，正常必填）

行為：
- `PlayingState` 允許
- 成功 -> 違規次數 +1，送出 `violation:recorded`

## 4) Server -> Client 事件格式

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

### `game:started`

```json
{
  "type": "game:started",
  "question": {
    "id": 1,
    "title": "test",
    "description": "",
    "starter_code": ""
  },
  "duration_seconds": 300
}
```

`question` 欄位 contract（暫定）：

| key | type | 說明 |
|---|---|---|
| `id` | int | 題目唯一 ID |
| `title` | str | 題目標題 |
| `description` | str | 題目描述（評分主要依據） |
| `starter_code` | str | 初始程式碼 |

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
      "score": 80,
      "penalty": 5,
      "final_score": 75,
      "feedback": "..."
    }
  }
}
```

## 5) 錯誤碼清單（目前）

| code | 說明 |
|---|---|
| `INVALID_EVENT` | 當前 state 不允許該事件 |
| `MISSING_PARAM` | 事件缺必要參數 |
| `NOT_HOST` | 非房主嘗試 `start` |
| `DUPLICATE_PLAYER` | 玩家重複加入 |
| `ROOM_FULL` | 房間人數已達上限 |

## 6) Pending（之後補齊）

以下會在後續 Phase 補齊：

- WebSocket endpoint URL 與 handshake 細節（Phase 4）
- REST 與 WS 欄位共用 schema（Phase 3/4）
- reconnect / replay / 斷線恢復策略（Phase 6）
