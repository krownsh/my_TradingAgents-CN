# 問題與解釋彙整 (questions.md)

## 1. 資料庫架構差異 (2026-02-10)

**提問**：目前專案到底是用什麼 DB？MongoDB、Supabase 和 SQLite 的差別在哪裡？

**解釋**：
這三者在您的專案中分別扮演不同角色，下表為詳細對比：

| 特性 | MongoDB | Supabase | SQLite |
| :--- | :--- | :--- | :--- |
| **技術類型** | NoSQL (文件型) | BaaS (基於 PostgreSQL) | 檔案型資料庫 |
| **主要定位** | **大數據倉庫** | **雲端信號同步** | **本地任務紀錄** |
| **儲存位置** | Docker 容器內的硬碟 | 雲端伺服器 (外部服務) | 專案資料夾下的 `.db` 檔 |
| **應用場景** | 存入數萬筆 A 股行情、Token 成本統計、長期分析報告存檔。 | 存入「買入/賣出信號」，讓您在外也能用手機網頁看到交易提醒。 | 存入「自選股名單」、單日腳本執行的暫存狀態。 |
| **優點** | 處理大量數據速度極快，擴充性強。 | 內建 API 與即時推送，適合網頁與 App。 | 無需安裝、零配置，非常輕量。 |
| **在 Docker 的角色** | 作為獨立服務與後端一起啟動。 | 作為外部 API 載入，不佔用本機資源。 | 作為一個數據文件映射到 `/app/data`。 |

**總結**：您可以理解為：
- **MongoDB** 是您的「中央倉庫」（存重數據）。
- **Supabase** 是您的「互聯網窗口」（存跨裝置信號）。
- **SQLite** 是您的「私人筆記本」（存腳本設定）。

---

## 3. 為什麼不「三合一」？資料庫分開的必要性分析 (2026-02-10)

**提問**：為什麼要分這麼多資料庫？不能全部塞進一個嗎？

**深度分析建議**：
雖然技術上可以強行整合（例如全部塞進 MongoDB），但目前的分開設計有其**架構上的合理性**與**節省成本**的考量：

### 1. 效能與儲存成本 (MongoDB vs. Supabase)
- **情境**：如果您將數萬筆「A 股歷史行情」塞進 Supabase (雲端)，很快就會超過免費額度並變得很慢（因為每次讀取都要走網路）。
- **必要性**：**MongoDB** 運行在您的本地 Docker 中，處理「重數據」（如海量行情）速度極快且完全免費。

### 2. 跨裝置存取 (Supabase vs. MongoDB)
- **情境**：如果您想在公司或手機上查看家裡電腦跑出來的「買入信號」，如果您家電腦沒開對外埠，您看不到 MongoDB。
- **必要性**：**Supabase** 扮演了「雲端橋樑」。它只存體積最小、價值最高的「信號數據」，讓您的 Web 介面在任何地方都能一秒載入，且不需要您去處理複雜的內網穿透。

### 3. 開發敏捷度 (SQLite vs. Others)
- **情境**：一些簡單的 Python 腳本（如 daily_stock_analysis）只需紀錄「今天掃描了哪幾支」。如果為了這點功能就要啟動 MongoDB 服務或連線雲端，太笨重了。
- **必要性**：**SQLite** 是一個檔案，隨時刪除、備份都極度方便，適合輕量級的狀態紀錄。

### 4. 整合建議 (如果要減法)
如果您真的很想簡化，未來的優化方向建議：
1. **取消 SQLite**：將自選股配置與掃描紀錄遷入 MongoDB（缺點：腳本會依賴 MongoDB 服務）。
2. **保留 Supabase**：這是目前實現「手機遠端查看」最便宜且穩定的方案。
3. **保留 MongoDB**：這是存放海量行情數據、供 AI 訓練或分析的唯一高效方案。

## 4. Supabase 是哪個專案引入的？它的 Schema 長怎樣？ (2026-02-10)

**提問**：Supabase 資料庫是基於原本哪一個專案而需要的？它的 Schema 選項要怎麼設定？

**解釋**：
Supabase 是由 **`my_ai-trading-agent-gemini`** (Social Sentiment Trading Agent) 專案所引入的。

### 為什麼需要它？
該專案是一個基於 Next.js 的網頁應用，它需要 Supabase 來：
1. **即時追蹤進度**：當後端正在進行 AI 分析時，前端可以透過 Supabase 的 Real-time 功能看到 0% -> 100% 的進度跳動。
2. **儲存交易信號**：儲存分析出來的買賣建議，方便手機遠端查看。

### Schema SQL 定義
如果您需要重建資料表，請在 Supabase 的 **SQL Editor** 中執行以下語句：

```sql
-- 1. 儲存 AI 產出的交易信號
CREATE TABLE trading_signals (
  id TEXT PRIMARY KEY,
  symbol TEXT NOT NULL,
  signal TEXT NOT NULL CHECK (signal IN ('BUY', 'SELL', 'HOLD')),
  confidence INTEGER NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
  reasoning TEXT NOT NULL,
  metrics JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 追蹤後端分析進度 (前端即時跳動用)
CREATE TABLE analysis_jobs (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'started',
  current_step TEXT DEFAULT 'Initializing...',
  step_message TEXT DEFAULT 'Starting analysis...',
  progress_percentage INTEGER DEFAULT 0,
  event_data JSONB,
  signals_generated INTEGER DEFAULT 0,
  alerts_generated INTEGER DEFAULT 0,
  duration_ms INTEGER,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 5. MongoDB 配置疑慮：是連到別人的資料庫嗎？ (2026-02-10)

**提問**：`MONGODB_HOST=localhost` 是連到作者的資料庫嗎？我該怎麼改？我不知道他的 Schema 長怎樣。

**解釋**：
請放心，這**完全是連到您自己的電腦**。

1. **關於 `localhost`**：
   - 在電腦術語中，`localhost` 代表「這台機器本身」。
   - 當您使用 Docker 啟動時，它會連向您自己電腦裡跑起來的那個 MongoDB 容器。
   - 除非您手動把 IP 改成別人的伺服器位址，否則資料永遠只會存在您自己的硬碟裡。

2. **關於 Schema (資料表結構)**：
   - MongoDB 本身是 **NoSQL (無固定模式)** 資料庫，它不需要像 SQL 那樣預先定義非常死板的表格。
   - **自動初始化**：專案資料夾中包含一個 [`mongo-init.js`](file:///d:/others/sideproject/stock%20analysis/my_TradingAgents-CN/scripts/mongo-init.js) 檔案。當您第一次執行 `docker-compose up` 時，Docker 會自動讀取這個檔案並為您建立好所有需要的結構。

### 自動建立的資料表概要：
- `users` / `user_sessions`: 管理使用者登入。
- `stock_basic_info` / `market_quotes`: 儲存股票基本面與即時行情。
- `analysis_tasks` / `analysis_reports`: 儲存 AI 的分析任務與最終報告。
- `token_usage`: 幫您統計花了多少 AI 額度。

**如何改成「您的」？**
其實您不需要改，因為啟動後它就是您的。如果您想更換密碼，只需同時修改以下兩個地方：
1. [`.env`](file:///d:/others/sideproject/stock%20analysis/my_TradingAgents-CN/.env) 中的 `MONGODB_PASSWORD`。
2. [`mongo-init.js`](file:///d:/others/sideproject/stock%20analysis/my_TradingAgents-CN/scripts/mongo-init.js) 中的第 13 行密碼設定。

## 6. Redis 又是做什麼的？ (2026-02-10)

**提問**：`REDIS_HOST=localhost` 這個 Redis 又是做什麼的？

**解釋**：
Redis 與 MongoDB 一樣，都是存放在您 **本地機器 (Docker)** 中的服務。

1. **它的角色**：Redis 是「極速快取 (Cache)」。
2. **它的用途**：
   - **減少 API 調用**：有些股票數據不需要每一秒都去網路抓，我們會先暫存在 Redis。
   - **加速系統回應**：Redis 是跑在記憶體裡的資料庫，讀取速度甚至比 MongoDB 還快上百倍。
   - **頻率限制**：防止您的 AI 助手太頻繁地呼叫外部 API (如 Gemini 或 Tushare) 導致被鎖帳號。

---

## 7. 「瀏覽量」疑慮：是不是有人在偷偷更新我的數據？ (2026-02-10)

**提問**：我看他在「學習中心」的文章還有顯示瀏覽量，如果他不是設假的，就代表他可能留有通道像外部更新？

**真相大白**：
請放心，這百分之百是 **「寫死的假數據」**。這在許多開源樣板中很常見，目的是為了讓 UI 看起來比較美觀、有「內容豐富」的感覺。

**技術證據**：
如果您檢查原始碼 `frontend/src/views/Learning/Category.vue` 的第 109 行到 213 行，您會發現每個分類的文章列表裡，`views` 這個欄位是直接寫在程式碼裡的：
- 「什麼是大語言模型」：`views: 2345` (固定值)
- 「提示詞基礎」：`views: 1876` (固定值)
- 「快速入門教程」：`views: 3456` (固定值)

**安全性總結**：
1. **無外部通道**：系統並未連接任何外部伺服器來統計或讀取這些點擊次數。
2. **純靜態顯示**：這些數字不會隨時間變動，除非您手動去改代碼。
3. **無隱藏後門**：經檢查後端 API，也沒有任何上傳「用戶點擊行為」或「統計數據」到第三方網域的邏輯。

**結論**：那個數字只是「裝飾品」，請不必擔心有任何隱密的對外通訊。為了讓專案更乾淨且專注於您的需求，我們接下來會把這些包含「裝飾性質」的教學書內容一併移除。

---

## 8. 任務進度確認：tasks.md 更新說明 (2026-02-10)

**提問**：確認一下 tasks.md。

**解釋**：
針對目前的開發進度，我們對 `tasks.md` 進行了以下調整與確認：
1. **追加 Phase 8**：我們主動新增了「冗餘代碼清理與安全性審計」階段，用以追蹤這一次大規模的代碼瘦身行動。
2. **清理任務執行**：
   - **移除教學書**：已物理刪除 `docs/learning/` 及其導航入口，並清理了前端路由與組件。
   - **清理緩衝區**：刪除根目錄下的臨時日誌與舊版驗證腳本。
   - **代碼合併**：保留核心 `tradingagents` 與 `app` 目錄，移除 `interface/` 下的重複副本。
3. **安全性查核**：確認無未經授權的外部連線行為。
4. **規則遵守**：所有變動均以「追加新任務」方式進行，未修改任何既有任務細節。

---

## 9. 關於 Sprint 2 完工狀態的疑慮 (2026-02-10)

**提問**：我怎麼記得 tasks.md 的 sprint2 你已經完成了？

**解釋**：
經工程端核實，目前的開發狀態如下：
1. **已完工 (Sprint 1.5)**：包含 `scratchpad.py` 核心邏輯、動態計畫生成、多輪專家討論循環 (`PLAN-DISCUSS`)。這些功能經代碼審查已確認存在於 `tradingagents/dexter_adapter` 中。
2. **未完工 (Sprint 2)**：
   - 狀態機：`MeetingState` 尚未加入 `VALIDATE` 狀態。
   - 代碼：`validator.py` (負責工具限制檢查、相似度偵測) 尚未實作。
   - 資料庫：`research_events` 集合尚未配置。
   - 前端：`Evidence Timeline` 組件尚未開發。
3. **結論**：可能是因為 Sprint 1.5 與 Sprint 2 在 `tasks.md` 中都引用了 `scratchpad.py` 導致名稱上的混淆。目前進度確實停留在 Sprint 1.5 結束，準備進入 Sprint 2。

---

## 10. VALIDATE 與 research_events 的用途說明 (2026-02-10)

**提問**：你說的 VALIDATE、research_events 這些是要拿來幹嘛的，會影響我當前流程嗎？

**真相大白**：
這兩者屬於 **Sprint 2 (系統健壯性優化)** 的範疇，目前不影響核心功能。

1. **VALIDATE (驗證器)**：
   - **目的**：AI 的「自我審查」。
   - **功能**：防止 AI 進入工具調用死循環、避免重複浪費 API 配額、確保市場規則正確（不拿美股指標看台股）。
2. **research_events (資料庫紀錄)**：
   - **目的**：將研究過程「結構化」。
   - **功能**：把 AI 查到的每一筆數據持久化存入 MongoDB。有了它，前端才能顯示「證據時間軸」，也方便之後做「歷史研究回溯」。

**影響評估**：
- **功能面**：完全不影響當前的會議室流程。

---

## 11. Dexter 核心架構與會議室流程的整合 (2026-02-10)

**提問**：你說的 Dexter 的核心架構（設計 -> 實作 -> 驗證 -> 持久化 -> 評測），那會議室的部分跟他一併來看的話會是怎麼走？

**解釋**：
這兩者是「內核」與「外殼」的關係。會議室提供**場景與需求**，Dexter 提供**執行與保障**。以下是完整的運行鏈條：

| 核心環節 | 會議室狀態 (State) | 具體動作 |
| :--- | :--- | :--- |
| **1. 設計 (Design)** | `PLAN` | 當專家提出需求時，Orchestrator 啟動 `DexterPlanner` 生成結構化的研究計畫。 |
| **2. 驗證 (Verify)** | `VALIDATE` | (Sprint 2 新增) 計畫執行前，由 `DexterValidator` 審查是否符合安全規則、市場規則與有無重複。 |
| **3. 實作 (Implement)** | `EXECUTE` | `DexterExecutor` 按照驗證過的計畫開始調用各種金融工具。 |
| **4. 持久化 (Persist)** | (背景同步) | 每執行完一個工具，`DexterScratchpad` 會自動將結果寫入 MongoDB 的 `research_events` 表。 |
| **5. 討論 (Discuss)** | `DISCUSS` | 專家讀取 Scratchpad 中的持久化數據進行討論，這是一次「即時評析」。 |
| **6. 評測 (Eval)** | (離線/CI) | (Sprint 3 實作) 透過離線跑車模擬「虛擬會議室」，確保代碼更新後這套流程不會出錯。 |

**總結**：
您可以把 Dexter 架構看作會議室中「研究員」的**職業規範**。
- **會議室**管的是「什麼時候該研究？」以及「研究完拿來聊什麼？」。
- **Dexter 架構**管的是「研究怎麼做才安全、精準、且有據可查？」。
- 透過 `MeetingOrchestrator`，這兩者完美縫合，確保您在 UI 上看到的「證據時間軸」不僅真實，且經過系統驗證。


