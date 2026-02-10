# 專案開發任務清單 (tasks.md)

本文件紀錄專案的開發進度與待辦事項。

## 任務守則
1. 既有任務未經允許不可隨意修改或移除。
2. 新任務只能以追加方式加入。

## 待辦任務 (TODO)

### 系統基礎
- [ ] 釐清並修復 `tasks.md` 遺失問題 <!-- id: 0 -->
- [ ] 持續維護 `questions.md` 記錄使用者問題 <!-- id: 1 -->

### Phase 1: Unified Data Contract (Data Models)
- [x] Create `tradingagents/models/core.py` with `SymbolKey` <!-- id: 3 -->
- [x] Update `tradingagents/models/stock_data_models.py` to support US/TW symbols <!-- id: 4 -->

### Phase 2: Provider Interface & MVP
- [x] Create `tradingagents/providers/interfaces.py` (MarketDataProvider) <!-- id: 5 -->
- [x] Create `tradingagents/providers/manager.py` (ProviderManager) <!-- id: 6 -->
- [x] Create `tradingagents/providers/tw/twse.py` (TWSE Provider) <!-- id: 7 -->
- [x] Create `tradingagents/providers/tw/tpex.py` (TPEx Provider) <!-- id: 8 -->
- [x] Create `tradingagents/providers/us/yahoo.py` (Yahoo Provider) <!-- id: 9 -->

### Phase 3: Market-Aware Infrastructure
- [x] Refactor `tradingagents/dataflows/cache/` to support `SymbolKey` <!-- id: 10 -->
- [x] Update `tradingagents/dataflows/interface.py` to use `ProviderManager` <!-- id: 11 -->

- [x] Create `tradingagents/services/market_rules.py` (Market Rules Service) <!-- id: 12 -->
- [x] Refactor Data Sync Tasks to be Market-Aware
- [x] Implement `sync_daily_bars` and verify <!-- id: 13 -->

### Phase 4: Strategy & Scanners Migration
- [x] Refactor Scanners to use `DataFlowInterface` (Market-Aware) <!-- id: 14 -->
    - [x] Update `ScreeningService` to `async` and use `DataFlowInterface`
    - [x] Update `EnhancedScreeningService` to await `ScreeningService`
    - [x] Ensure `DatabaseScreeningService` falls back to `ScreeningService` for non-CN markets
- [x] Refactor Strategy Engine tools to support `SymbolKey` and `DataFlowInterface` <!-- id: 15 -->
    - [x] Refactor `get_stock_market_data_unified`
    - [x] Refactor `get_stock_fundamentals_unified`
    - [x] Refactor `get_stock_news_unified`
    - [x] Refactor `get_stock_sentiment_unified`
- [x] Verify End-to-End Workflow (Sync -> Cache -> Interface -> Strategy) <!-- id: 16 -->
    - [x] Verify CN Market (600519)
    - [x] Verify US Market (AAPL)
    - [x] Verify TW Market (2330)

### Phase 5: JCP Feature Integration (Meeting Room) <!-- id: 17 -->
- [x] Phase 1: Tool Infrastructure <!-- id: 18 -->
    - [x] Implement Python ToolRegistry <!-- id: 19 -->
    - [x] Register market data tools (quote, bars, news, sentiment) <!-- id: 20 -->
- [x] Phase 2: Meeting Orchestration <!-- id: 21 -->
    - [x] Implement Moderator (小韭菜) logic <!-- id: 22 -->
    - [x] Implement Meeting Orchestrator state machine <!-- id: 23 -->
    - [x] Define Expert Agents (Technical, Fundamental, etc.) <!-- id: 24 -->
- [x] Phase 3: Memory System <!-- id: 25 -->
    - [x] Implement MongoDB symbol-specific memory storage <!-- id: 26 -->
    - [x] Implement Key Facts and Rolling Summaries logic <!-- id: 27 -->
- [x] Phase 4: API & Web Integration <!-- id: 28 -->
    - [x] Implement FastAPI Meeting Router <!-- id: 29 -->
    - [x] Implement WebSocket real-time discussion streaming <!-- id: 30 -->
- [x] Phase 5: Front-end UI Implementation <!-- id: 31 -->
    - [x] Implement Meeting Room UI (Vue.js) <!-- id: 32 -->
    - [x] Integrate real-time report display <!-- id: 33 -->

### Phase 6: Dexter Research Agent Integration <!-- id: 34 -->
> **整合計畫**: 參考 `dexter_integration_plan.md`

#### Sprint 1: Tool Adapter + Minimal Research Mode (2週) <!-- id: 35 -->
- [x] 建立 `tradingagents/dexter_adapter/` 目錄結構 <!-- id: 36 -->
- [x] 實作 Tool Adapter Schema (`schemas.py`) <!-- id: 37 -->
- [x] 實作 Price Adapter (`tools/prices.py`) <!-- id: 38 -->
  - [ ] `dexter_get_price_snapshot` (market.quote)
  - [ ] `dexter_get_prices` (market.bars)
- [x] 實作 News Adapter (`tools/news.py`) <!-- id: 39 -->
  - [x] US: market.news
  - [x] TW: mops.announcements
- [x] 實作 Fundamentals Adapter (`tools/fundamentals.py`) <!-- id: 40 -->
  - [x] US: income_statement, balance_sheet, cash_flow
  - [x] TW: MISSING fallback
- [x] Python 重寫 Dexter Planner (`planner.py`) <!-- id: 41 -->
- [x] 新增 PLAN state 至會議室狀態機 <!-- id: 42 -->
- [x] 前端顯示研究計畫結構 <!-- id: 43 -->

#### Sprint 1.5: 動態規劃增強 (已完成) <!-- id: 50 -->
- [x] Scratchpad 上下文管理 (`scratchpad.py`) <!-- id: 51 -->
  - [x] 多計畫儲存機制
  - [x] 工具結果追蹤
  - [x] LLM 上下文格式化
- [x] 多輪 PLAN-DISCUSS 循環 <!-- id: 52 -->
  - [x] 專家數據請求解析 (`<data_request>` 標記)
  - [x] 動態計畫生成與執行
  - [x] Orchestrator 整合 (max 3 rounds)
- [x] 前端多計畫顯示 <!-- id: 53 -->
  - [x] Meeting Store 擴展（researchPlans[]）
- [x] ResearchPlanPanel 折疊面板

#### Sprint 2: VALIDATE + Scratchpad (已完成) <!-- id: 44 -->
- [x] 新增 VALIDATE state 至狀態機 <!-- id: 45 -->
- [x] 實作 DexterValidator (`validator.py`) <!-- id: 46 -->
  - [x] 工具呼叫限制檢查
  - [x] 查詢相似度偵測
  - [x] Market-aware 驗證規則
- [x] 實作 Python Scratchpad MongoDB 自動同步 (`scratchpad.py`) <!-- id: 47 -->
- [x] 建立 MongoDB research_events 與 research_sessions 表 <!-- id: 48 -->
- [ ] 前端 Evidence Timeline 組件 <!-- id: 49 --> (併入後續 UI 優化階段)

#### Sprint 3: Evals + CI Integration (已完成) <!-- id: 50 -->
- [x] 建立 US/TW 測試題庫 (20 題) <!-- id: 51 -->
- [x] 實作自動化評測腳本 (`runner.py`) <!-- id: 52 -->
- [x] 整合 GitHub Actions 評測工作流 <!-- id: 53 -->
- [x] 實作評分機制與 Markdown 報告生成 <!-- id: 54 -->

### Phase 7: 未來功能 <!-- id: 55 -->
- [ ] Dexter Skills 系統整合 (DCF, 技術分析工作流程) <!-- id: 56 -->
- [ ] 前端研究模式切換開關 <!-- id: 57 -->
- [ ] 歷史研究報告匯出 (PDF/JSON) <!-- id: 58 -->

### Phase 8: 冗餘代碼清理與安全性審計 <!-- id: 59 -->
- [x] 移除「學習中心/教學書」相關導航與組件 (Frontend) <!-- id: 60 -->
- [x] 刪除 `docs/learning/` 及其相關資源文件 <!-- id: 61 -->
- [x] 清理根目錄冗餘 `.log`, `.txt`, `.bak` 及驗證腳本 <!-- id: 62 -->
- [x] 檢查並清理 `tradingagents` 中不必要的過期模組 <!-- id: 63 -->
- [x] 進行全局安全性掃描，確保無未授權的外部連線 (Beaconing) <!-- id: 64 -->

## 已完成任務 (DONE)
- [x] 專案架構初步檢視與 Docker 必要性解釋 (2026-02-09) <!-- id: 2 -->

