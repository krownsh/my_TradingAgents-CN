# TradingAgents-CN 系統連通性檢查手冊

此文件用於引導用戶逐一檢查前端介面與後端 API 的連通性。

## 1. 儀表板與基礎數據 (Dashboard)
- **前端視圖**: `src/views/Dashboard/index.vue`
- **後端路由**: `app/routers/usage_statistics.py`, `app/routers/stocks.py`
- **驗證動作**:
  1. 進入首頁，檢查「Token 消耗」與「分析次數」是否顯示（API: `/api/statistics/token-usage`）。
  2. 檢查下方股票列表是否能正常載入（API: `/api/stocks`）。

## 2. 股票分析流程 (Stock Analysis)
- **前端視圖**: `src/views/Analysis/SingleAnalysis.vue`
- **後端路由**: `app/routers/analysis.py`
- **關鍵服務**: `app/services/simple_analysis_service.py`
- **驗證動作**:
  1. 輸入股票代碼，觀察是否有模糊搜尋建議（API: `/api/stocks/search`）。
  2. 設定分析級別並提交，檢查是否產生任務 ID 並導向任務中心。

## 3. 任務中心與實時監控 (Task Center)
- **前端視圖**: `src/views/Tasks/TaskCenter.vue`
- **後端路由**: `app/routers/queue.py`, `app/routers/websocket_notifications.py`
- **驗證動作**:
  1. 檢查任務中心是否列出剛剛提交的分析任務。
  2. 觀察進度條是否隨時間增加（這需依賴 WebSocket 或 SSE 連線）。

## 4. 研究會議室 (Meeting Room)
- **前端視圖**: `src/views/MeetingRoom/index.vue`
- **後端路由**: `app/routers/meeting.py`
- **關鍵服務**: `tradingagents/meeting/orchestrator.py`
- **驗證動作**:
  1. 進入會議室，選擇股票並啟動。
  2. 檢查對話視窗是否出現各個專家（例如基本面分析師、技術面分析師）的發言。

## 5. 系統配置 (Settings)
- **前端視圖**: `src/views/Settings/ConfigManagement.vue`
- **後端路由**: `app/routers/config.py`
- **驗證動作**:
  1. 檢查 LLM 提供商列表是否能正常讀取與儲存。
  2. 測試「測試連線」按鈕是否能正確回報模型是否可用。

---
**檢查狀態**: 待用戶截圖確認。
