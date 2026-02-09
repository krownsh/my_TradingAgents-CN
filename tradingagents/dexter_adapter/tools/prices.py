"""
Price Adapter - 價格數據適配器

將 Dexter 的價格查詢需求適配到 TradingAgents-CN 的 DataFlowInterface。
支援 US + TW 雙市場的即時報價與歷史價格。
"""

from datetime import datetime, timedelta
from typing import Optional
import logging

from tradingagents.dexter_adapter.schemas import (
    PriceInput,
    DexterToolOutput
)
from tradingagents.dataflows.interface_v2 import DataFlowInterface
from tradingagents.models.core import SymbolKey

logger = logging.getLogger(__name__)


async def dexter_get_price_snapshot(symbol_key: str) -> DexterToolOutput:
    """
    獲取股票即時報價（Snapshot）
    
    對應 Dexter 的 getPriceSnapshot，透過 DataFlowInterface 獲取最新報價。
    
    Args:
        symbol_key: 標準化格式，如 'US:AAPL' 或 'TW:2330'
        
    Returns:
        DexterToolOutput: 包含報價資料、品質、來源等資訊
        
    Example:
        >>> result = await dexter_get_price_snapshot("US:AAPL")
        >>> print(result.data["price"], result.quality)
    """
    try:
        # 解析 symbol_key
        market, symbol = symbol_key.split(':', 1)
        
        # 建立 DataFlowInterface
        interface = DataFlowInterface()
        
        # 獲取最新報價
        quote_data = await interface.get_stock_quote(symbol=symbol, market=market)
        
        if not quote_data:
            return DexterToolOutput(
                data=None,
                quality="MISSING",
                source_provider="unknown",
                asof=datetime.utcnow(),
                market=market,
                symbol=symbol,
                message=f"無法獲取 {symbol_key} 的報價資料"
            )
        
        # 判斷資料品質
        quality = "EOD"  # 預設為收盤資料
        if quote_data.get("is_realtime"):
            quality = "REALTIME"
        elif quote_data.get("delayed"):
            quality = "DELAYED"
        
        # 提取資料時間戳
        asof = quote_data.get("timestamp")
        if isinstance(asof, str):
            asof = datetime.fromisoformat(asof.replace('Z', '+00:00'))
        elif not isinstance(asof, datetime):
            asof = datetime.utcnow()
        
        return DexterToolOutput(
            data={
                "symbol": symbol,
                "price": quote_data.get("price", quote_data.get("close")),
                "open": quote_data.get("open"),
                "high": quote_data.get("high"),
                "low": quote_data.get("low"),
                "close": quote_data.get("close"),
                "volume": quote_data.get("volume"),
                "change": quote_data.get("change"),
                "change_percent": quote_data.get("change_percent"),
                "market_cap": quote_data.get("market_cap"),
            },
            quality=quality,
            source_provider=quote_data.get("provider", "unknown"),
            asof=asof,
            market=market,
            symbol=symbol,
            source_urls=quote_data.get("source_urls", [])
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
        logger.error(f"Error fetching price snapshot for {symbol_key}: {e}")
        return DexterToolOutput(
            data=None,
            quality="MISSING",
            source_provider="error",
            asof=datetime.utcnow(),
            message=f"獲取報價失敗: {str(e)}"
        )


async def dexter_get_prices(
    symbol_key: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timeframe: str = "1d"
) -> DexterToolOutput:
    """
    獲取歷史價格數據（Bars）
    
    對應 Dexter 的 getPrices，透過 DataFlowInterface 獲取歷史 K 線資料。
    
    Args:
        symbol_key: 標準化格式，如 'US:AAPL' 或 'TW:2330'
        start_date: 開始日期 (YYYY-MM-DD)，預設為 30 天前
        end_date: 結束日期 (YYYY-MM-DD)，預設為今日
        timeframe: 時間框架，預設 "1d"（日線）
        
    Returns:
        DexterToolOutput: 包含歷史價格資料
        
    Example:
        >>> result = await dexter_get_prices("TW:2330", start_date="2024-01-01")
        >>> print(len(result.data["bars"]))
    """
    try:
        # 解析 symbol_key
        market, symbol = symbol_key.split(':', 1)
        
        # 處理日期範圍
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_dt = datetime.now() - timedelta(days=30)
            start_date = start_dt.strftime("%Y-%m-%d")
        
        # 建立 DataFlowInterface
        interface = DataFlowInterface()
        
        # 獲取歷史價格
        bars_data = await interface.get_historical_bars(
            symbol=symbol,
            market=market,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe
        )
        
        if not bars_data or not bars_data.get("bars"):
            return DexterToolOutput(
                data=None,
                quality="MISSING",
                source_provider="unknown",
                asof=datetime.utcnow(),
                market=market,
                symbol=symbol,
                message=f"無法獲取 {symbol_key} 於 {start_date} ~ {end_date} 的歷史資料"
            )
        
        # 判斷資料品質（歷史資料通常為 EOD）
        quality = "EOD"
        
        return DexterToolOutput(
            data={
                "symbol": symbol,
                "bars": bars_data.get("bars", []),
                "count": len(bars_data.get("bars", [])),
                "timeframe": timeframe,
                "start_date": start_date,
                "end_date": end_date,
            },
            quality=quality,
            source_provider=bars_data.get("provider", "unknown"),
            asof=datetime.utcnow(),
            market=market,
            symbol=symbol,
            source_urls=bars_data.get("source_urls", [])
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
        logger.error(f"Error fetching price history for {symbol_key}: {e}")
        return DexterToolOutput(
            data=None,
            quality="MISSING",
            source_provider="error",
            asof=datetime.utcnow(),
            message=f"獲取歷史價格失敗: {str(e)}"
        )
