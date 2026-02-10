# Docker 快速啟動指南

透過 Docker，您可以在一分鐘內啟動整個 TradingAgents-CN 系統，包含資料庫、後端 API 與前端界面。

## 1. 環境準備

1. 確保已安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。
2. 複製根目錄下的樣板：
   ```bash
   cp .env.example .env
   ```
3. 在 `.env` 中填入您的 `GOOGLE_GEMINI_API_KEY` 與其他必要的 API Key。

## 2. 一鍵啟動

在專案根目錄執行：
```bash
docker-compose up -d
```

## 3. 訪問服務

- **前端界面**: [http://localhost:3000](http://localhost:3000)
- **後端 API**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redis 管理**: [http://localhost:8081](http://localhost:8081)
- **MongoDB 管理**: [http://localhost:8082](http://localhost:8082)

## 4. 資料庫說明

系統採用多庫並存設計，但在 Docker 下已實現自動路由：
- **MongoDB**: 自動啟動並初始化，用於存儲行情與 Token 數據。
- **SQLite**: 自動儲存於 Docker Volume (`/app/data`)，重啟後數據不丟失。
- **Supabase**: 若未填寫 API Key，系統會自動切換為本地模式，不影響核心功能。

## 5. 常用命令

- **查看日誌**: `docker-compose logs -f backend`
- **停止服務**: `docker-compose down`
- **更新鏡像並重啟**: `docker-compose up -d --build`
