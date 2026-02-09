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

## 已完成任務 (DONE)
- [x] 專案架構初步檢視與 Docker 必要性解釋 (2026-02-09) <!-- id: 2 -->
