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
