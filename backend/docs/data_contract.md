# Data Contract — Phase 3 Step 3-1

對齊既有 core 型別與 SQLite ORM 欄位，供 Step 3-2～3-8 實作時參考。  
Core（`Room` / `states`）與 Phase 2 adapter **不在此 step 修改**。

**來源對照：**

| 領域 | 程式碼 | 協定文件 |
|---|---|---|
| 題目 | `core.ports.QuestionPayload`, `ExampleCase` | `protocol.md` § `game:started.question` |
| 房間狀態 | `core.states.*`, `Room.transition_to` | `protocol.md` § `state:changed.state` |
| 提交與評分 | `Room.submissions`, `Room._judge_all_submissions` | `protocol.md` § `game:result.results` |

---

## 1. Question ↔ `QuestionPayload`

ORM 表名：`questions`

| DB 欄位 | SQL 型別 | Python / `QuestionPayload` | 必填 | 備註 |
|---|---|---|---|---|
| `id` | `INTEGER` PK | `id: int` | ✓ | 題庫唯一 ID；seed 與 `get_by_id` 用 |
| `title` | `TEXT` | `title: str` | ✓ | |
| `description` | `TEXT` | `description: str` | ✓ | AI 評分主要依據（`Room._judge_all_submissions` 傳入 judge） |
| `examples` | `JSON` | `examples: list[ExampleCase]` | ✓ | 見下方 JSON schema |
| `constraints` | `JSON` | `constraints: list[str]` | ✓ | 字串陣列 |
| `starter_code` | `JSON` | `starter_code: dict[str, str]` | ✓ | key = 語言代碼（如 `python`、`js`） |

### `examples` JSON schema（對齊 `ExampleCase`）

```json
[
  {
    "input": "nums = [2,7,11,15], target = 9",
    "output": "[0,1]",
    "explanation": "Because nums[0] + nums[1] = 9."
  }
]
```

| JSON key | 型別 | 對應 |
|---|---|---|
| `input` | string | `ExampleCase["input"]` |
| `output` | string | `ExampleCase["output"]` |
| `explanation` | string \| null | `ExampleCase["explanation"]` |

### `starter_code` JSON 範例

```json
{
  "python": "def solve(nums, target):\n    pass",
  "js": "function solve(nums, target) {\n  return [];\n}"
}
```

### ORM → API 轉換

- Repository / schema 讀出後組成 `QuestionPayload`（dict），欄位名稱**不 rename**。
- `Room._validate_question_contract` 與 `test_ports_contract` 要求的 key 集合必須完整覆蓋。

---

## 2. Room

ORM 表名：`rooms`

| DB 欄位 | SQL 型別 | Core / 協定對應 | 必填 | 備註 |
|---|---|---|---|---|
| `code` | `TEXT` PK | `Room.room_code` | ✓ | 房間代碼（如 `INT01`）；WebSocket 分房 key |
| `status` | `TEXT` | `type(Room.state).__name__` | ✓ | 見下方 enum |
| `created_at` | `DATETIME` (UTC) | （新增，core 目前無） | ✓ | 建立時間；`POST /rooms` 時寫入（Phase 4） |

### `status` 允許值

與 `state:changed` 廣播值一致，存**完整 class 名稱**（不簡化）：

| 值 | Core state | 說明 |
|---|---|---|
| `LobbyState` | `LobbyState` | 等待加入 |
| `ReadyState` | `ReadyState` | 人數已滿，可開始 |
| `PlayingState` | `PlayingState` | 進行中 |
| `JudgingState` | `JudgingState` | 評分中 |
| `ResultState` | `ResultState` | 已結束 |

新建房間預設：`LobbyState`。

### 刻意不 persist 的 in-memory 欄位

以下仍只存在 `Room` aggregate，**不在 `rooms` 表**（Phase 3 範圍）：

- `players`, `question`, `submissions`, `violations`, `timer_task`
- 遊戲規則：`max_players`, `game_duration_seconds`, `violation_penalty`（來自 `config.Settings`）

---

## 3. Submission

ORM 表名：`submissions`

一房間一玩家一筆提交（同一 `room_code` + `player` 唯一）。對應一局結束後的持久化紀錄。

| DB 欄位 | SQL 型別 | Core / 協定對應 | 必填 | 備註 |
|---|---|---|---|---|
| `room_code` | `TEXT` FK → `rooms.code` | `Room.room_code` | ✓ | 邏輯關聯房間 |
| `player` | `TEXT` | `Room.submissions` 的 key | ✓ | 玩家識別（目前為 display name 字串） |
| `code` | `TEXT` | `Room.submissions[player]` | ✓ | 提交的原始碼 |
| `score` | `REAL` | `game:result.results[player].score` | ✓ | AI 原始分數 0–10 |
| `feedback` | `TEXT` | judge 回傳（見下方） |  | 可 NULL；LLM / mock judge 有產出 |
| `penalty` | `INTEGER` | `results[player].penalty` |  | 可 NULL；`violations × violation_penalty` |
| `final_score` | `REAL` | `results[player].final_score` |  | 可 NULL；`max(score - penalty, 0)` |

### 建議複合唯一鍵

`(room_code, player)` — 與目前「每房固定兩位玩家、各提交一次」流程一致。

### 資料來源對照（結算時）

```
Room.submissions[player]          →  submissions.code
IJudgeService.judge(...)["score"] →  submissions.score
同上 ["feedback"]                 →  submissions.feedback   （見 Known gaps）
violations × violation_penalty    →  submissions.penalty
max(score - penalty, 0)           →  submissions.final_score
```

未提交的玩家：`code` 為空字串（與 `_judge_all_submissions` 現行行為一致），`score` 仍會由 judge 評估空 code。

---

## 4. 型別對照摘要

| Python | SQLite / SQLAlchemy |
|---|---|
| `int` | `Integer` |
| `str` | `Text` |
| `float` | `Float` / `REAL` |
| `list[...]`, `dict[...]` | `JSON`（SQLAlchemy 2.x `JSON` 型別） |
| `datetime` (UTC) | `DateTime(timezone=True)` 或 naive UTC + 應用層約定 |

---

## 5. Known gaps（記錄 drift，Step 3-1 不修改 core）

| 項目 | 現況 | Phase 3 建議 |
|---|---|---|
| `JudgeResult` | `ports.py` 僅宣告 `score` | `submissions.feedback` 仍 persist；日後可擴充 `JudgeResult`（非 3-1 範圍） |
| `Room._judge_all_submissions` | 結果 dict 不含 `feedback` | persist 時 repository 需直接讀 judge 回傳或擴充 core（Phase 4 接線時處理） |
| `game:result` 廣播 | 不含 `feedback` | DB 可先存；協定廣播留 `protocol.md` Pending |
| 房間 ↔ 題目 | core 不存 `question_id` | 題目僅在 `PlayingState` 記憶體；submission 表不 FK 題目（一局一題、房間即上下文） |

---

## 6. Step 3-1 驗收

- [x] Question / Room / Submission 三實體欄位與 core、protocol 對照完成
- [x] JSON 欄位結構與 `QuestionPayload` / `ExampleCase` 對齊
- [x] `status` 與 state class 名稱對齊
- [x] Submission 含可選 `penalty`、`final_score`、`feedback`
- [ ] 後續 step：依本文件實作 `db/session.py`、`db/models.py`、`db/schemas.py`、`db/repositories/`
