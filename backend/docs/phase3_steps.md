# Phase 3 — 資料層（SQLite + Repositories）

目標：房間、題目、提交可持久化；每個 step 對應一個小 PR，方便 code review。  
Core（`Room` / `states`）與 Phase 2 adapter 在此階段**不修改**，僅新增資料層。

資料層程式碼集中於 **`db/`** package（`session`、`models`、`schemas`、`repositories/`），與 `core/`、`adapters/` 對齊。

---

# Step 3-1：確認資料契約

對齊既有型別與 DB 欄位，避免 ORM 與 `core/ports.py` drift。

- **Question** ↔ `QuestionPayload`：`id`、`title`、`description`、`examples`、`constraints`、`starter_code`（`examples` / `constraints` / `starter_code` 建議 JSON 欄位）
- **Room**：`code`（PK）、`status`（對齊 state 名稱或簡化 enum）、`created_at`
- **Submission**：`room_code`、`player`、`code`、`score`、`feedback`（可選 `penalty`、`final_score`）
- 產出：在 `docs/` 或 PR 描述中記錄欄位對照表（可附在本 step PR）

---

# Step 3-2：做 db/session.py

建立 async SQLite 連線基礎設施。

- `db/session.py`：async engine、`async_sessionmaker`、依 `config.database_url`
- `db/__init__.py` re-export 常用 API（`init_db`、`get_session` 等）
- 提供 `get_session()`（或同等功能）供 repository 使用
- `init_db()` / `create_all`：開發環境建表（不含 seed）
- 驗收：pytest 可建立 in-memory 或 temp file DB 並開 session

---

# Step 3-3：做 db/models.py（Question）

先實作題目表（後續 seed 與 `question_repository` 依賴此表）。

- SQLAlchemy model：`Question`（繼承 `db.session.Base`）
- 欄位覆蓋 Step 3-1 契約；複雜結構用 JSON
- 驗收：`init_db` 後可 insert / select 一筆題目

---

# Step 3-4：做 db/models.py（Room + Submission）

補齊其餘兩張表。

- ORM `Room`（表 `rooms`）：`code`、`status`、`created_at` — 與 `core.room.Room` 區分，import 時注意命名
- `Submission`：`room_code`、`player`、`code`、`score`、`feedback`（FK 或邏輯關聯 `room_code`）
- 驗收：三表皆可建表；基本 CRUD 可手動或測試驗證

---

# Step 3-5：做 db/schemas.py

REST / API 用的 Pydantic 模型，與 ORM 分離。

- 例如：`RoomCreate`、`RoomRead`、`QuestionRead`、`SubmissionRead`
- 與 `protocol.md` / `QuestionPayload` 對齊，不引入 FastAPI 路由（留 Phase 4）
- 驗收：schema 可從 ORM instance `model_validate` 轉換

---

# Step 3-6：做 question_repository

題目 CRUD + 隨機出題查詢。

- `db/repositories/question_repository.py`
- 至少：`get_by_id`、`list_all`、`get_random`（或 `pick_random`）
- 驗收：repository 單測（in-memory / temp SQLite）

---

# Step 3-7：做 room_repository

房間 CRUD。

- `db/repositories/room_repository.py`
- 至少：`create`、`get_by_code`、`update_status`、`list_recent`（可選）
- 驗收：建立房間 → 查詢 → 更新 status 單測通過

---

# Step 3-8：做 submission_repository

提交紀錄 CRUD。

- `db/repositories/submission_repository.py`
- 至少：`create`、`list_by_room`、`get_by_room_and_player`
- 驗收：同一 `room_code` 可存多筆 submission 並查回

---

# Step 3-9：種子題目 seed

將題庫寫入 DB，供之後取代純 mock 題目。

- 來源可複用 `adapters/mock_question.py` 的 `DEFAULT_QUESTIONS`
- 實作：`scripts/seed_questions.py` 或 startup hook（擇一，避免重複 seed）
- 驗收：執行 seed 後 `question_repository.list_all()` 非空

---

# Step 3-10：整合驗收測試

確認資料層端到端可用，仍不碰 `Room` 遊戲流程。

- pytest：建立 room → 寫入 submission → 重開 session 仍可查詢
- 覆蓋：三個 repository 至少各一個整合情境
- 驗收：Phase 3 完成標準——**重啟 / 新 session 後紀錄仍可查詢**

---

## Phase 3 完成後（留 Phase 4）

- `IQuestionService` 改接 DB repository（非 Phase 3 範圍）
- `POST /rooms` 建立房間時寫入 `room_repository`
- 遊戲結束時 persist submission
