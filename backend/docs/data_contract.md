# Data Contract — Phase 3

對齊既有 core 型別與 SQLite ORM 欄位。  
**資料庫只持久化題庫（`questions` 表）**；房間與對戰狀態全在記憶體。

**來源對照：**

| 領域 | 持久化 | 程式碼 | 協定文件 |
|---|---|---|---|
| 題目 | SQLite | `core.ports.QuestionPayload`, `ExampleCase` | `protocol.md` § `game:started.question` |
| 房間 / 狀態 | 記憶體 | `core.room.Room`, `core.states.*` | `protocol.md` § `state:changed` |
| 提交 / 評分 | 記憶體 | `Room.submissions`, `_judge_all_submissions` | `protocol.md` § `game:result` |

### 斷線重連（不依賴 DB）

| 情境 | 行為 |
|---|---|
| 一人斷線、另一人仍連線 | `Room` 物件仍在記憶體；重連後由 `ConnectionManager` 恢復 WebSocket |
| 兩人皆斷線 | 房間消失、遊戲結束；**不**從資料庫恢復 |

---

## 1. Question ↔ `QuestionPayload`（唯一 DB 表）

ORM 表名：`questions`

| DB 欄位 | SQL 型別 | Python / `QuestionPayload` | 必填 | 備註 |
|---|---|---|---|---|
| `id` | `INTEGER` PK | `id: int` | ✓ | 題庫唯一 ID；seed 與 `get_by_id` 用 |
| `title` | `TEXT` | `title: str` | ✓ | |
| `description` | `TEXT` | `description: str` | ✓ | AI 評分主要依據 |
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

### ORM → API 轉換

- Repository / schema 讀出後組成 `QuestionPayload`（dict），欄位名稱**不 rename**。
- `Room._validate_question_contract` 與 `test_ports_contract` 要求的 key 集合必須完整覆蓋。

---

## 2. Room（僅記憶體，無 DB 表）

由 `core.room.Room` aggregate 持有，Phase 4 由 composition root（`wiring` / `main`）以 dict 或 registry 管理生命週期。

| 欄位 / 狀態 | 位置 | 備註 |
|---|---|---|
| `room_code` | `Room.room_code` | WebSocket 分房 key |
| `state` | `Room.state` | `LobbyState` … `ResultState` |
| `players`, `question`, `submissions`, `violations` | `Room` 實例 | 遊戲進行中資料 |
| 遊戲規則 | 建構子注入 | 來自 `config.Settings` |

---

## 3. 提交與評分（僅記憶體，無 DB 表）

結算結果經 `game:result` 廣播；不寫入 SQLite。

| 資料 | 位置 |
|---|---|
| 玩家程式碼 | `Room.submissions[player]` |
| 分數 / 扣分 / 最終分 | `_judge_all_submissions` → `game:result.results` |
| Judge 評語 | judge adapter 回傳（目前未廣播，見 `protocol.md` Pending） |

---

## 4. 型別對照摘要（Question）

| Python | SQLite / SQLAlchemy |
|---|---|
| `int` | `Integer` |
| `str` | `Text` |
| `list[...]`, `dict[...]` | `JSON` |

---

## 5. Known gaps（不修改 core）

| 項目 | 現況 |
|---|---|
| `JudgeResult` | `ports.py` 僅宣告 `score`；mock/LLM judge 另回 `feedback` |
| `game:result` 廣播 | 不含 `feedback`（見 `protocol.md` Pending） |

---

## 6. 驗收 checklist

- [x] Question 欄位與 `QuestionPayload` / `ExampleCase` 對齊
- [x] Room / Submission 明確標示為記憶體，不建 DB 表
- [x] 斷線重連規則：依 `ConnectionManager` + in-memory `Room`，非 DB
- [x] 後續：`db/schemas.py`（Question）、`question_repository`、seed、整合測試；schema 以 Alembic 管理（Step 3-4 ✅）
