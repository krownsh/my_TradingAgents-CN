# 問題與解釋紀錄 (questions.md)

本文件用於記錄使用者的提問以及系統的解釋，作為後續重點提示與參考。

## 2026-02-09

### 提問：完整檢視一下這個專案。他不是網頁端功能嗎?為何會需要docker

**解釋：**

雖然 `TradingAgents-CN` 提供了一個網頁介面給使用者操作，但它的後端架構比一般的「網頁端功能」要複雜得多。以下是為什麼需要 Docker 的幾個核心理由：

1.  **多組件協作（Orchestration）：**
    這個專案不僅僅是前端網頁，它是由四個核心組件組成的完整系統：
    *   **Frontend (Vue 3):** 使用者介面。
    *   **Backend (FastAPI/Python):** 核心交易智能體邏輯、資料抓取與處理。
    *   **MongoDB:** 用於持久化儲存股票數據、歷史分析報告與系統配置。
    *   **Redis:** 用於高速緩存與 SSE/WebSocket 實時通知系統。
    透過 Docker Compose，使用者只需一個指令就能同時啟動並正確連結這四個服務。

2.  **依賴環境的一致性（Python 環境）：**
    後端智能體使用了大量的 Python 科學計算與金融分析庫（如 Pandas, TA-Lib 等）。其中 TA-Lib 等函式庫在不同作業系統（尤其是 Windows）上的安裝過程非常繁瑣且容易報錯。Docker 確保了後端在容器內的 Linux 環境中運行，避免了開發與部署時的環境差異問題。

3.  **資料庫與緩存的自動化配置：**
    使用 Docker 不需要手動在主機上安裝、配置並運行 MongoDB 和 Redis Server。Docker Compose 會自動拉取鏡像並根據配置設置好帳號密碼與資料持久化卷（Volumes）。

4.  **網路隔離與安全性：**
    Docker 為這些服務創建了一個內部的虛擬網路，確保組件之間的通訊安全且不與主機的其他應用發生衝突。

---

### 提問：我接著要怎麼啟動呢？

**解釋：**

根據專案目前的架構（v1.0.0-preview），你有三種啟動與使用方式：

1.  **使用 Docker (推薦，適合完整體驗)：**
    這是最簡單的方式，會自動啟動前端、後端、MongoDB 與 Redis。
    *   **指令：** `docker-compose up -d --build` (因為代碼有更新，建議加上 `--build`)。
    *   **訪問：**
        *   **前端介面：** `http://localhost:3000`
        *   **後端 API 文檔：** `http://localhost:8000/docs`
    *   **優點：** 自動處理資料庫 (MongoDB/Redis) 環境，適合需要完整 UI 功能的使用者。

2.  **本地開發啟動 (適合開發與調試)：**
    如果你希望在本地直接運行系統：
    *   **後端：** 在根目錄執行 `python -m app` (預設啟動在 8000 端口)。
    *   **前端：** 進入 `frontend` 目錄，執行 `yarn dev` 或 `npm run dev` (預設啟動在 3000 或 5173 端口)。
    *   **前提：** 需確保本地已啟動 MongoDB (27017) 與 Redis (6379)。

3.  **單次腳本測試 (CLI)：**
    如果你只想透過程式碼直接分析特定的股票（例如台股 2330），可以修改並執行根目錄的 `main.py`：
    ```python
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    # ... 配置 ...
    ta = TradingAgentsGraph(debug=True, config=config)
    # 測試台股 2330
    _, decision = ta.propagate("2330", "2024-05-10")
---

### 提問：所以我只要直接 docker-compose up -d --build 就可以用了嗎？

**解釋：**

**還差一個關鍵步驟**。在執行 Docker 指令之前，你需要先準備好**環境變數文件 (`.env`)**，否則 AI 智能體將因為沒有 API Key 而無法運作。

具體流程如下：

1.  **創建 `.env` 文件**：
    將專案中的範例文件複製一份：
    ```powershell
    copy .env.example .env
    ```

2.  **配置 API Key**：
    打開 `.env` 文件，填入你使用的 AI 模型密鑰（例如 `GOOGLE_API_KEY` 或 `OPENAI_API_KEY`）。
    *   如果你想測試台股，請確保 `GOOGLE_API_KEY` (Gemini) 已填入。
    *   若有 `TUSHARE_TOKEN` (A股) 或 `FINNHUB_API_KEY` (美股) 也建議一併填入以獲得最佳體驗。

3.  **執行啟動指令**：
    完成配置後，再執行：
    ```powershell
    docker-compose up -d --build
    ```

4.  **驗證配置 (可選)**：
    啟動後，你可以進入後端容器執行測試腳本，確保一切正常：
    ```powershell
    docker exec -it tradingagents-backend python -m cli.main test
    ```
    print(decision)
    ```

