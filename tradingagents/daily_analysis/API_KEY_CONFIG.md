# Daily Analysis API Key 配置說明

## 📝 環境變數配置位置

API Key 和配置應寫在專案根目錄的 `.env` 文件中。

### 配置文件位置
```
my_TradingAgents-CN/
├── .env              ← 在這裡配置（主要配置文件）
├── .env.example      ← 參考範例
└── tradingagents/
    └── daily_analysis/
```

## 🔑 必要的 API Keys

### 1. AI 分析 API（擇一即可）

#### Gemini API（推薦，免費額度較高）
```ini
# Gemini API Key (從 Google AI Studio 獲取)
# https://aistudio.google.com/app/apikey
DAILY_GEMINI_API_KEY=your_gemini_api_key_here

# 或使用主系統的 Gemini Key（如果沒設置 DAILY_ 前綴會自動使用）
GEMINI_API_KEY=your_gemini_api_key_here
```

#### OpenAI API（可選）
```ini
# OpenAI API Key（如需使用 OpenAI）
DAILY_OPENAI_API_KEY=your_openai_api_key_here
DAILY_OPENAI_MODEL=gpt-4-turbo-preview

# 或使用主系統的 OpenAI Key
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. 新聞搜索 API（可選，至少配置一個）

#### Tavily Search（推薦，每月 1000 次免費）
```ini
# Tavily API Key
# https://tavily.com/
DAILY_TAVILY_API_KEY=your_tavily_api_key_here
```

#### SerpAPI（可選，每月 100 次免費）
```ini
# SerpAPI Key
# https://serpapi.com/
DAILY_SERPAPI_KEY=your_serpapi_key_here
```

### 3. 推送通知（可選）

#### 企業微信 Webhook
```ini
# 企業微信機器人 Webhook URL
DAILY_WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxx
```

#### 飛書 Webhook
```ini
# 飛書機器人 Webhook URL
DAILY_FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx
```

#### Telegram Bot（可選）
```ini
# Telegram Bot Token
DAILY_TELEGRAM_BOT_TOKEN=your_bot_token
DAILY_TELEGRAM_CHAT_ID=your_chat_id
```

## 📋 其他配置選項

### 自選股列表
```ini
# 自選股票代碼列表（逗號分隔）
DAILY_STOCK_LIST=600519,000001,TW:2330,US:AAPL,US:NVDA

# 或使用主系統的股票列表
STOCK_SYMBOLS=TW:2330,US:AAPL
```

### 分析參數
```ini
# 最大併發數（預設：3）
DAILY_MAX_WORKERS=3

# 啟用即時行情（預設：true）
DAILY_ENABLE_REALTIME_QUOTE=true

# 啟用籌碼分佈分析（預設：false，需要額外數據源）
DAILY_ENABLE_CHIP_DISTRIBUTION=false

# 報告類型（simple/full，預設：simple）
DAILY_REPORT_TYPE=simple

# 單股推送（預設：false，設為 true 會每分析一隻股票就推送一次）
DAILY_SINGLE_STOCK_NOTIFY=false
```

## 🌐 數據源配置（可選）

### Tushare Pro（A股數據，需要積分）
```ini
# Tushare Token
# https://tushare.pro/register
DAILY_TUSHARE_TOKEN=your_tushare_token
```

### FinMind（台股數據，免費）
```ini
# FinMind API Key（可選，未設置則使用公開額度）
# https://finmindtrade.com/
DAILY_FINMIND_API_KEY=your_finmind_key
```

## 📄 完整 .env 範例

```ini
# =========================================
# Daily Stock Analysis Configuration
# =========================================

# === AI API Keys (必要，擇一) ===
DAILY_GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# DAILY_OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# === 新聞搜索 API (可選，至少一個) ===
DAILY_TAVILY_API_KEY=tvly-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# DAILY_SERPAPI_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# === 自選股配置 ===
DAILY_STOCK_LIST=600519,000001,TW:2330,US:AAPL,US:NVDA

# === 分析參數 ===
DAILY_MAX_WORKERS=3
DAILY_ENABLE_REALTIME_QUOTE=true
DAILY_ENABLE_CHIP_DISTRIBUTION=false
DAILY_REPORT_TYPE=simple
DAILY_SINGLE_STOCK_NOTIFY=false

# === 推送通知 (可選) ===
DAILY_WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxx
# DAILY_FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx
# DAILY_TELEGRAM_BOT_TOKEN=123456789:XXXXXXXXXXXXXXXXXXXXXXXXXXX
# DAILY_TELEGRAM_CHAT_ID=123456789

# === 數據源 API (可選) ===
# DAILY_TUSHARE_TOKEN=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# DAILY_FINMIND_API_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

## ⚙️ 配置優先級

Daily Analysis 使用以下優先級讀取配置：

1. **DAILY_** 前綴的環境變數（最高優先級）
2. 無前綴的主系統環境變數（fallback）
3. 程式內建預設值（最後 fallback）

例如：
- 如果設置了 `DAILY_GEMINI_API_KEY`，則使用此值
- 如果沒有，則嘗試讀取 `GEMINI_API_KEY`
- 如果都沒有，則啟動時會提示錯誤

## 🔒 安全提醒

1. **永遠不要** 將 `.env` 文件提交到 Git
2. `.env` 已在 `.gitignore` 中排除
3. 使用 `.env.example` 作為模板，不包含真實 Key
4. API Key 應妥善保管，定期輪換

## ✅ 驗證配置

創建後，可以使用以下命令驗證配置是否正確：

```bash
# 測試配置載入
python test_daily_analysis_api.py

# 或直接測試 API
curl http://localhost:8000/api/daily/config
```

## 🆘 常見問題

### Q: 沒有設置任何 API Key 會怎樣？
A: AI 分析功能無法使用，但可以獲取數據（dry_run 模式）

### Q: 搜索 API 都不設置會怎樣？
A: 新聞搜索功能會被停用，但不影響股價分析

### Q: 可以只用免費的 API 嗎？
A: 可以！Gemini（每天 1500 次）+ Tavily（每月 1000 次）完全免費

### Q: 台股需要特別配置嗎？
A: 不需要，FinMind 數據源免費可用，無需 API Key
