# TradingAgents-CN 啟動指南

這份指南將協助你完成 TradingAgents-CN 的環境設定與啟動流程。

## 1. 環境設定 (最重要)

專案依賴環境變數來運作，你需要先建立 `.env` 設定檔。

在專案根目錄執行以下指令：

```bash
cp .env.example .env
```

接著使用文字編輯器打開 `.env` 檔案，填入以下必要資訊：

*   **GOOGLE_GEMINI_API_KEY** (或其他 LLM Key)：用於 AI 模型調用。
*   **TAVILY_API_KEY**：用於網路搜尋功能。
*   **TUSHARE_TOKEN**：用於獲取 A 股數據。

> **注意**：如果不填寫這些 Key，系統啟動後可能會報錯或無法執行分析。

## 2. 啟動方式

### 選項 A：完整 Docker 啟動 (推薦)

這會自動啟動後端 (Backend)、前端 (Frontend)、資料庫 (MongoDB) 與快取 (Redis)。

在專案根目錄執行：

```bash
docker-compose up -d --build
```

*   `-d`: 在背景執行。
*   `--build`: 強制重新建置映像檔 (確保包含最新的程式碼變更)。

啟動完成後，你可以透過瀏覽器訪問：

*   **前端頁面**: [http://localhost:3000](http://localhost:3000)
*   **後端 API 文件**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Redis 管理介面**: [http://localhost:8081](http://localhost:8081) (如果 docker-compose.yml 有啟動 redis-commander)

### 選項 B：混合開發模式 (適合前端開發)

如果你想要修改前端程式碼並即時預覽，可以只用 Docker 啟動後端服務，前端則在本地運行。

1.  **啟動後端與資料庫** (使用 Docker)：
    ```bash
    # 只啟動必要服務
    docker-compose up -d backend mongodb redis
    ```

2.  **啟動前端** (在本地)：
    ```bash
    cd frontend
    npm install  # 如果還沒安裝依賴
    npm run dev
    ```
    
    前端將運行在：[http://localhost:5173](http://localhost:5173) (Vite 預設端口，可能與 Docker 版不同)

## 3. 常見問題排除

### 錯誤：`yaml: line 25: did not find expected key`
這是 `docker-compose.yml` 格式錯誤導致的 (已修復)。請確保檔案內的 `environment` 區塊沒有混合使用 Map (`KEY: VAL`) 和 List (`- KEY`) 語法。

### 錯誤：資料庫連接失敗
請檢查 `.env` 中的 `MONGODB_HOST` 與 `REDIS_HOST` 設定。
*   如果是 Docker 啟動，通常設為 `mongodb` 和 `redis` (容器名稱)。
*   如果是本地啟動後端，則設為 `localhost`。

### 重啟服務
如果修改了 `.env` 或程式碼，建議重啟服務：

```bash
docker-compose down
docker-compose up -d --build
```

## 4. 最近修復與更新 (Troubleshooting & Fixes Applied)

以下是最近針對啟動問題所做的修復，請確保你的程式碼包含這些變更：

### 1. Backend 啟動錯誤
- **`yaml: line 25`**: 修正了 `docker-compose.yml` 中 `backend` 服務的 `environment` 格式錯誤。
- **`ModuleNotFoundError: No module named 'backend'`**: 在 `app/main.py` 中暫時註解掉了缺失的 `daily_analysis` 模組引用。
- **`IndentationError`**: 修正了 `tradingagents/meeting/states.py` 中 `MeetingState` Enum 的縮排錯誤。
- **`SyntaxError`**: 修正了 `tradingagents/providers/us/yahoo.py` 中 `get_basic_info` 和 `get_news` 方法的語法結構。
- **`NameError`**: 在 `twse.py` 和 `tpex.py` 中補上了缺失的 `StockNews` 和 `NewsCategory` 引用。

### 2. 資料庫連接
- **`Connection refused`**: 更新了 `.env` 檔案，將 `MONGODB_HOST` 從 `localhost` 改為 `mongodb`，`REDIS_HOST` 改為 `redis`，以確保 Docker 容器內部能正確通訊。

### 3. 前端構建錯誤
- **`SyntaxError`**: 修正了 `frontend/src/views/DailyAnalysis/index.vue` 中按鈕 `@click` 事件的語法錯誤 (`refresh ConfigStocks` -> `refreshConfigStocks`)。

### 4. 輔助工具
- **`async_utils.py`**: 新增了 `tradingagents/utils/async_utils.py`，提供 `run_async` 函數來解決同步調用異步函數的問題 (如 Jupyter/Uvicorn 環境)。

## 5. 驗證服務狀態

啟動後，請執行以下命令確認所有服務皆正常運行 (Status 為 Up 或 healthy)：

```bash
docker-compose ps
```

預期輸出應包含：
- `tradingagents-backend` (healthy)
- `tradingagents-frontend` (healthy 或 starting)
- `tradingagents-mongodb` (healthy)
- `tradingagents-redis` (healthy)

若發現服務狀態為 `Exit` 或 `Restarting`，請查看詳細日誌：

```bash
docker-compose logs --tail 50 backend
docker-compose logs --tail 50 frontend
```

