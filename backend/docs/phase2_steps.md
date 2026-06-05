# Step 2-1:先定義/確認契約
鎖定 IJudgeService.judge()、IQuestionService.get_random_question()、INotifyService.notify_room() 的 input/output 與錯誤策略（特別是 judge 回傳格式）。

# Step 2-2：做 mock_question
先用固定題庫/隨機題，保證符合 Room._validate_question_contract 要求（id/title/description/starter_code）。

# Step 2-3：做 mock_judge
固定分數 + feedback，確保 Phase 1/2 本地流程可跑，不依賴外部 API。

# Step 2-4：做 claude_judge
封裝 prompt、timeout、JSON 解析、格式驗證與 fallback（API 失敗時要有可控錯誤）。

# Step 2-5：做 websocket_notify
把 notify_room(room_code, event) 委派給 ConnectionManager 廣播。

# Step 2-6：DI 組裝切換策略

能透過設定在 mock / claude judge 間切換，不改 core。

# Step 2-7：測試
adapter 單測 + Room 整合測試（至少覆蓋 game:started、submission:received、game:result、error event）。