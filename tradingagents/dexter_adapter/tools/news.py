"""
News Adapter - 新聞數據適配器

將 Dexter 的新聞查詢需求適配到 TradingAgents-CN 的新聞系統。
US 市場使用 market.news，TW 市場使用 mops.announcements。
"""

from datetime import datetime
from typing import Optional
import logging

from tradingagents.dexter_adapter.schemas import DexterToolOutput
from tradingagents.dataflows.interface_v2 import DataFlowInterface

logger = logging.getLogger(__name__)


async def dexter_get_news(
    symbol_key: str,
    limit: int = 10,
    start_date: Optional[str] = None
) -> DexterToolOutput:
    """
    獲取股票新聞與公告
    
    對應 Dexter 的 getNews，根據市場選擇資料來源：
    - US: market.news
    - TW: mops.announcements + market.news(如可用)
    
    Args:
        symbol_key: 標準化格式，如 'US:AAPL' 或 'TW:2330'
        limit: 返回數量，預設 10
        start_date: 開始日期 (YYYY-MM-DD)，可選
        
    Returns:
        DexterToolOutput: 包含新聞/公告列表
        
    Example:
        >>> result = await dexter_get_news("TW:2330", limit=5)
        >>> print(len(result.data["news"]))
    """
    try:
        # 解析 symbol_key
        market, symbol = symbol_key.split(':', 1)
        
        # 建立 DataFlowInterface
        interface = DataFlowInterface()
        
        news_items = []
        provider = "unknown"
        
        # US 市場：使用 market.news
        if market == "US":
            try:
                news_data = await interface.get_stock_news(
                    symbol=symbol,
                    market=market,
                    limit=limit
                )
                
                if news_data and news_data.get("news"):
                    news_items = news_data.get("news", [])
                    provider = news_data.get("provider", "market.news")
            except Exception as e:
                logger.warning(f"Failed to fetch US news for {symbol}: {e}")
        
        # TW 市場：優先使用 mops.announcements
        elif market == "TW":
            try:
                # 獲取 MOPS 公告
                announcements = await interface.get_tw_announcements(
                    symbol=symbol,
                    limit=limit
                )
                
                if announcements and announcements.get("data"):
                    news_items = announcements.get("data", [])
                    provider = "mops"
            except Exception as e:
                logger.warning(f"Failed to fetch TW announcements for {symbol}: {e}")
                
            # 嘗試補充一般新聞（如果 MOPS 資料不足）
            if len(news_items) < limit:
                try:
                    news_data = await interface.get_stock_news(
                        symbol=symbol,
                        market=market,
                        limit=limit - len(news_items)
                    )
                    
                    if news_data and news_data.get("news"):
                        news_items.extend(news_data.get("news", []))
                        provider = f"{provider}+market.news" if provider != "unknown" else "market.news"
                except Exception as e:
                    logger.warning(f"Failed to fetch TW news for {symbol}: {e}")
        
        # CN 市場
        elif market == "CN":
            try:
                news_data = await interface.get_stock_news(
                    symbol=symbol,
                    market=market,
                    limit=limit
                )
                
                if news_data and news_data.get("news"):
                    news_items = news_data.get("news", [])
                    provider = news_data.get("provider", "market.news")
            except Exception as e:
                logger.warning(f"Failed to fetch CN news for {symbol}: {e}")
        
        # 檢查是否有資料
        if not news_items:
            return DexterToolOutput(
                data=None,
                quality="MISSING",
                source_provider=provider,
                asof=datetime.utcnow(),
                market=market,
                symbol=symbol,
                message=f"無法獲取 {symbol_key} 的新聞/公告"
            )
        
        return DexterToolOutput(
            data={
                "symbol": symbol,
                "market": market,
                "news": news_items,
                "count": len(news_items),
            },
            quality="EOD",  # 新聞通常為歷史資料
            source_provider=provider,
            asof=datetime.utcnow(),
            market=market,
            symbol=symbol,
            source_urls=[]
        )
        
    except ValueError as e:
        logger.error(f"Invalid symbol_key format: {symbol_key}, error: {e}")
        return DexterToolOutput(
            data=None,
            quality="MISSING",
            source_provider="error",
            asof=datetime.utcnow(),
            message=f"symbol_key 格式錯誤: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error fetching news for {symbol_key}: {e}")
        return DexterToolOutput(
            data=None,
            quality="MISSING",
            source_provider="error",
            asof=datetime.utcnow(),
            message=f"獲取新聞失敗: {str(e)}"
        )
