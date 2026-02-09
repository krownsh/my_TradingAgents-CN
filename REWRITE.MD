一、目標與設計原則
目標

先跑通 US+TW 的資料能力（行情、K 線、基本資料、公告/新聞的最低可用集）。

完全移除 A 股依賴（tushare/akshare/baostock 之類的 provider），避免再被牽著走。

做成 Provider 可插拔：未來要換資料源（券商、付費行情、內網資料庫）只改 provider，不改上層 agent / UI / 策略。

保持 TradingAgents-CN 的平台能力（同步灌庫、快取、批次分析、篩選器、匯出）可用。

設計原則（規範守則總綱）

Domain first：先定義系統內部的資料模型（Quote/Bar/Fundamentals/News），外部 API 都要轉成這個模型。

Provider isolated：任何外部資料源（TWSE/TPEX/MOPS/Finnhub/YFinance/FinancialDatasets）都只能在 provider 層出現。

Market-aware：所有工具/服務必須接受 market（US/TW）與標準化 symbol，不允許「靠猜」。

可追溯：任何會影響結論的資料取得，必須可重現（記錄 provider、請求參數、時間戳、版本）。

可回歸：每次換 provider 或改 mapping，不准只靠肉眼；要有 golden tests。

降級策略：資料缺失要有明確 fallback（例如即時拿不到就改用盤後 close），但必須回報「資料品質等級」。

二、建議流程（分階段、每階段都有「完成標準」）
Phase 0：盤點與切割（1 次性工作）
你要做的事

在 TradingAgents-CN 內部找出與中國資料源耦合的模組（通常是 dataflows/providers、data_sources/manager、adapters、同步任務）。

列出現有上層會用到的資料類別：

股票清單 / 基本資料

日K / 分K

即時 quote（如果有）

財報/指標

新聞/公告

完成標準

你能指出「上層服務」對「資料層」的所有入口（哪些函式/endpoint 會取資料）。

把 A 股 provider 呼叫點定位完畢（之後才能一刀切掉）。

Phase 1：建立「統一資料契約」與 Symbol 標準化（最關鍵）

這步先做，後面會省掉大量重工。

1) Symbol Canonicalization 規範（必寫成 code + 文檔）

內部統一用這種資料結構（範例）：

SymbolKey:
  market: "US" | "TW"
  exchange: "NASDAQ" | "NYSE" | "AMEX" | "TWSE" | "TPEX"
  code: "AAPL" | "2330" | "006208"
  asset_type: "EQUITY" | "ETF" | "ADR" | ...
  currency: "USD" | "TWD"


規則：

使用者輸入可以是 2330、2330.TW、TSMC、台積電，但一律要轉成 SymbolKey。

TW 市場必須知道 TWSE/TPEX，不能只存 .TW 模糊尾碼。

任意資料表主鍵一律用 SymbolKey（或其 hash），避免「同代碼跨市場撞名」。

2) 統一資料模型（Domain Models）

你至少要定義這些（Pydantic model / dataclass）：

Quote：timestamp、last、open、high、low、prev_close、volume、turnover、bid/ask（可選）、quality（見下）

Bar：t、o、h、l、c、v（可加 vwaps）

CompanyProfile：name、industry、listing_exchange、shares_outstanding（能拿多少算多少）

Fundamentals：季度/年度主表（先抓關鍵指標，別一開始求全）

NewsItem / Announcement：source、title、published_at、url、symbols、summary（可後算）

3) 資料品質等級（Quality Level）規範

每個取數結果都要帶 quality：

REALTIME（逐筆/即時）

DELAYED

EOD（盤後）

ESTIMATED

MISSING

這對 agent 很重要：它需要知道「我是在用盤後資料」還是「即時」。

完成標準

全系統任何地方都不再直接使用「原始 ticker 字串」當主鍵。

任一 provider 回傳都能被轉成統一模型（哪怕資訊缺失，也要標 quality）。

Phase 2：Provider Manager（可插拔 + fallback）與 US/TW Provider MVP
Provider 介面規範（你未來擴充的根基）

建立抽象介面（例如 MarketDataProvider）：

必需方法（MVP）：

search_symbol(query) -> list[SymbolKey]

get_quote(symbol: SymbolKey) -> Quote

get_bars(symbol, timeframe, start, end) -> list[Bar]

get_profile(symbol) -> CompanyProfile | None

可選（後續補）：

get_fundamentals(symbol, period) -> Fundamentals

get_actions(symbol) -> CorporateActions

get_news(symbol, start, end) -> list[NewsItem]

get_announcements(symbol, start, end) -> list[Announcement]

Provider Manager 規範

以 market 做路由：US → US provider chain；TW → TW provider chain

支援 fallback chain：例如 US：Primary=finnhub → fallback=yfinance；TW：Primary=TWSE/TPEX → fallback=付費/券商

fallback 必須保留 provenance：你要知道這筆資料最後是從哪個 provider 拿的

台股 Provider MVP：TWSE + TPEX

TWSE OpenAPI（上市）(openapi.twse.com.tw
)

TPEx OpenAPI（上櫃）(tpex.org.tw
)

先做到：股票清單 + 日K/日成交資訊 + 盤後 quote（close/成交量），就能啟動大量功能。

美股 Provider MVP：你可以先用簡單可用的

TradingAgents-CN 本身常見搭配 finnhub/yfinance（取決於原專案現況與你手上的 key/額度）。
策略是：先跑通，再優化品質。

完成標準

同一組上層 API（例如「個股詳情」頁）能同時查 US 與 TW 的行情與基本資料。

provider chain 可配置（config 驅動，不寫死）。

Phase 3：同步灌庫 / 快取 / 任務排程改成 market-aware

TradingAgents-CN 很強的是「平台化」：同步、快取、批次、篩選器。你要保留這些就得把任務也市場化。

任務規範

任務都要帶 market 與 symbol universe（US universe / TW universe）

交易日曆要拆開（US holidays vs TW holidays）

同步頻率可不同：TW 官方多盤後，US 可做到較高頻

Redis/Mongo key 也要帶市場與 symbol key

完成標準

啟動排程後，TW/US 的資料都能落庫、快取命中、批次篩選不混淆。

Phase 4：台股制度（Rules Engine）接入風控與報告

台股跟美股差異大，你若不把制度做成“可查詢規則”，agent 很容易講錯。

規範

建立 MarketRulesService（或 tool）：

trading hours（TW/US）

price limit（台股有漲跌幅）

lot size（整股/零股）

tax/fee model（至少抽象：sell tax exists in TW）

完成標準

報告/風控/回測（若有）引用的是規則服務，不是 prompt 常識。

Phase 5：公告/財報/新聞（台股重點在 MOPS）

台股研究的「官方第一手」是公告/重大訊息/財報（MOPS），你應該把它當成 filings。

先做 AnnouncementsProvider（哪怕只是索引 + url + title + time）

後面再做結構化（營收、財報表欄位）

完成標準：

台股個股頁/報告能引用 MOPS 類型的來源（至少能列出公告清單）