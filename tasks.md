# Task: Restore Missing `daily_analysis` Module

The `daily_analysis` module is missing from the backend routing, causing `ModuleNotFoundError`. This module is required by the Frontend's "Daily Analysis" page.

## 1. Analysis & Preparation
- [ ] Explore `tradingagents/daily_analysis` to understand available services.
- [ ] Identify the endpoints required by Frontend (`frontend/src/views/DailyAnalysis/index.vue`):
    - `GET /api/daily/config`
    - `POST /api/daily/analyze`
    - `POST /api/daily/market-review`
    - `GET /api/daily/history`
- [ ] Check `tradingagents/daily_analysis` internal imports and fix legacy references (e.g. `web.services`).

## 2. Implementation: Fix Internal Imports
- [ ] Scan `tradingagents/daily_analysis` for broken imports (e.g. `from web.services import ...`).
- [ ] specific file: `tradingagents/daily_analysis/bot/commands/analyze.py` -> fix import to `app.services.analysis_service`.

## 3. Implementation: Create Router
- [ ] Create `app/routers/daily_analysis.py`.
- [ ] Implement `GET /config`: Return system config for daily analysis.
- [ ] Implement `POST /analyze`: Trigger stock analysis (integration with `AnalysisService` or `StockAnalyzer`).
- [ ] Implement `POST /market-review`: Trigger market review (integration with `MarketAnalyzer`).
- [ ] Implement `GET /history`: return analysis history.

## 4. Integration
- [ ] Uncomment `app/main.py` imports for `daily_analysis`.
- [ ] Restart backend and verify endpoints.

## 5. Verification
- [ ] Test Frontend "Daily Analysis" page.
- [ ] Verify "Refresh Config" button.
- [ ] Verify "Analyze" button.
- [ ] Verify "Market Review" button.
