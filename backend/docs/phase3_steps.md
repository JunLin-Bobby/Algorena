# Phase 3 — 資料層（SQLite 題庫）

目標：**題庫**可持久化；房間與對戰狀態維持在記憶體。每個 step 對應一個小 PR。  
Core（`Room` / `states`）與 Phase 2 adapter 原則上不修改；**例外**：Step 3-6.5 擴充 `QuestionPayload`（加 `difficulty`）時需更新 `Room._validate_question_contract`。

資料層程式碼集中於 **`db/`** package（`session`、`models`、`schemas`、`repositories/`、`seed`）。  
**Schema 變更以 Alembic migration 管理**，不用 `create_all` 作為正式建表方式。

### 題庫管理策略（Step 3-6.5 / 3-7 設計決策）

| 項目 | 決定 |
|------|------|
| 題目來源 | 單檔 `backend/data/questions.yaml`（Git 管版本） |
| `difficulty` | 納入 `QuestionPayload`，`game:started` 廣播；`Literal["easy", "medium", "hard"]` |
| 同步時機 | App startup（`main.py` lifespan） |
| Upsert 識別 | **`id`**（非 `title`；改 title 仍 UPDATE 同一列） |
| 刪題 | Startup **prune** — 刪掉 YAML 未列出的 id |
| 版本控制 | Git only（不加 `version` / `is_active` / event log） |
| Seed 模組 | `db/seed.py` + Pydantic `QuestionSeed` 驗證 YAML |
| 暫不做 | 分檔 YAML、CI sync、`scripts/` CLI |

### 不在 Phase 3 範圍

- Room / Submission **不建 DB 表、不做 repository**
- 斷線重連由 `ConnectionManager` + in-memory `Room` 處理（Phase 6 可補協定細節）

---

# Step 3-1：確認資料契約 ✅

- **Question** ↔ `QuestionPayload`（唯一 DB 表）
- Room、Submission 僅記憶體 — 見 `docs/data_contract.md`

---

# Step 3-2：做 db/session.py ✅

- async engine、`async_sessionmaker`、依 `config.database_url`
- `get_session()` 供 repository 使用
- ~~`init_db()` / `create_all`~~ → Step 3-4 起 **`init_db()` 改呼叫 Alembic `upgrade head`**

---

# Step 3-3：做 db/models.py（Question） ✅

- SQLAlchemy model：`Question`（繼承 `db.session.Base`）
- 驗收：表結構就緒，待 Step 3-4 initial migration 建表後可 insert / select

---

# Step 3-4：Alembic migration 設定 ✅

以 Alembic 管理 `questions` 表 schema（版本化、可重現）。

- 依賴：`alembic`（加入 `pyproject.toml`）
- 設定：`alembic.ini`、`alembic/env.py`
  - `target_metadata` → `db.session.Base.metadata`（需 import `db.models` 註冊 model）
  - DB URL → `config.Settings.database_url`（async URL；migration 執行時依 Alembic 慣例使用 sync driver 或官方 async 設定）
- 產生 **initial revision**：建立 `questions` 表（對齊 Step 3-1 / `Question` model）
- 開發／部署建表：`alembic upgrade head`（取代 `init_db()` 的 `create_all`）
- 測試：pytest fixture 對 in-memory 或 temp file DB 執行 `upgrade head` 後再測 insert / select
- 移除 `create_all`；`init_db()` 改為 thin wrapper 呼叫 `upgrade head`（保留同名 convenience API）
- 驗收：
  - 空 DB 執行 `alembic upgrade head` 後存在 `questions` 表
  - `alembic downgrade -1` 可還原（若 initial down revision 有定義）
  - 現有 model 相關測試改走 migration 後仍通過

---

# Step 3-5：做 db/schemas.py ✅

REST / API 用的 Pydantic 模型，與 ORM 分離。

- 至少：`QuestionRead`（可選 `QuestionCreate` 供日後管理題庫）
- 與 `QuestionPayload` 對齊；不引入 FastAPI 路由（留 Phase 4）
- 驗收：schema 可從 ORM `Question` instance `model_validate` 轉換

---

# Step 3-6：做 question_repository ✅

- `db/repositories/question_repository.py`
- 至少：`get_by_id`、`list_all`、`get_random`（或 `pick_random`）
- 驗收：repository 單測（in-memory / temp SQLite；fixture 先 `alembic upgrade head`）

---

# Step 3-6.5：擴充 Question 契約（difficulty） ✅

- `core.ports.QuestionPayload` 加 `difficulty: Literal["easy", "medium", "hard"]`
- `db.models.Question`、`db.schemas.QuestionRead` 對齊
- Alembic migration：`questions` 表加 `difficulty TEXT NOT NULL`
- `core.room.Room._validate_question_contract` `required_keys` 加 `"difficulty"`
- 更新 `docs/data_contract.md`、`docs/protocol.md`（`game:started.question`）
- `DEFAULT_QUESTIONS` / 相關測試補 `difficulty`
- 驗收：`test_ports_contract`、`test_schemas_question`、`test_models_question` 通過

---

# Step 3-7：題庫 YAML + startup seed ✅

- 依賴：`pyyaml`（加入 `pyproject.toml`）
- 題目檔：`backend/data/questions.yaml`（從 `DEFAULT_QUESTIONS` 搬移並補 `difficulty`）
- 實作：`db/seed.py`
  - `load_questions_from_yaml()` — Pydantic `QuestionSeed` 驗證；id 不可重複
  - `seed_questions(session_factory)` — **upsert by `id`** + **prune**（刪 YAML 未列 id）
  - 空 YAML 防護：`questions: []` 時 skip prune、log warning（避免刪光題庫）
- 啟動：`main.py` lifespan — `init_db` → `seed_questions` → `build_app_dependencies`；`engine` / `session_factory` 掛 `app.state`
- 驗收：`tests/test_seed.py`（insert / update / prune / idempotent / duplicate id / empty yaml）

### Seed 行為摘要

| 情境 | 結果 |
|------|------|
| 第一次啟動，YAML 10 題 | 10 × INSERT |
| YAML 增至 20 題 | id 1–10 UPDATE，11–20 INSERT |
| YAML 改 title（id 不變） | UPDATE 同一列 |
| YAML 拿掉某 id | startup 後 DELETE 該列 |
| 相同 YAML 跑兩次 | 冪等 |

---

# Step 3-8：整合驗收測試 ✅

- pytest：migration → seed → 新 session 仍可 `list_all` / `get_random`
- 驗收：`tests/test_phase3_integration.py` — 新 session 題庫與 YAML 一致；重啟後再次 seed 仍冪等

---

## Phase 3 完成後（留 Phase 4）

- `IQuestionService` 改接 DB `question_repository`
- `POST /rooms` 建立 in-memory `Room`（不寫 DB）
- 斷線重連邏輯擴充 `ConnectionManager` / room registry
- 部署流程：啟動 app（lifespan 內 `alembic upgrade head` + seed）；改題目 = 編輯 YAML → commit → restart
