# Phase 3 — 資料層（SQLite 題庫）

目標：**題庫**可持久化；房間與對戰狀態維持在記憶體。每個 step 對應一個小 PR。  
Core（`Room` / `states`）與 Phase 2 adapter 在此階段**不修改**。

資料層程式碼集中於 **`db/`** package（`session`、`models`、`schemas`、`repositories/`）。  
**Schema 變更以 Alembic migration 管理**，不用 `create_all` 作為正式建表方式。

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

# Step 3-7：種子題目 seed

- 來源：`adapters/mock_question.py` 的 `DEFAULT_QUESTIONS`
- 實作：`scripts/seed_questions.py` 或 startup hook（擇一，避免重複 seed）
- 前置：目標 DB 已 `alembic upgrade head`
- 驗收：執行 seed 後 `question_repository.list_all()` 非空

---

# Step 3-8：整合驗收測試

- pytest：migration → seed → 新 session 仍可 `list_all` / `get_random`
- 驗收：Phase 3 完成標準——**重啟 / 新 session 後題庫仍可查詢**

---

## Phase 3 完成後（留 Phase 4）

- `IQuestionService` 改接 DB `question_repository`
- `POST /rooms` 建立 in-memory `Room`（不寫 DB）
- 斷線重連邏輯擴充 `ConnectionManager` / room registry
- 部署流程：`alembic upgrade head` →（可選）seed → 啟動 API
