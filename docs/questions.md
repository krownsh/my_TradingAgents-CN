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

**結論**：它就像系統的「捷徑筆記」，把最近常用的資料存在手邊，讓整體反應更靈敏。同樣地，只要執行 `docker-compose up`，它就會自動啟動並配置好，您不需要手動安裝。
