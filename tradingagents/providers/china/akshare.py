import logging
from typing import List, Optional, Any, Dict, Union
from datetime import datetime
import pandas as pd

from tradingagents.models.core import SymbolKey, TimeFrame, MarketType
from tradingagents.models.stock_data_models import StockDailyQuote, StockBasicInfo, StockRealtimeQuote, StockNews, NewsCategory
from tradingagents.providers.interfaces import MarketDataProvider
from tradingagents.dataflows.providers.china.akshare import get_akshare_provider

logger = logging.getLogger(__name__)

class AKShareDataProviderV2(MarketDataProvider):
    """
    AKShare 数据提供者 (V2)
    封装了原有的 AKShareProvider 以符合 MarketDataProvider 接口。
    """
    
    def __init__(self):
        super().__init__("akshare")
        # 直接获取全局实例，避免重复初始化
        self.v1_provider = get_akshare_provider()

    @property
    def supported_markets(self) -> List[MarketType]:
        return [MarketType.CN]

    async def connect(self) -> bool:
        return await self.v1_provider.connect()

    async def disconnect(self):
        await self.v1_provider.disconnect()

    async def get_bars(
        self, 
        symbol: SymbolKey, 
        timeframe: TimeFrame, 
        start: datetime, 
        end: datetime
    ) -> List[StockDailyQuote]:
        """获取历史K线数据"""
        try:
            # yfinance interval mapping
            # AKShare typically uses daily, weekly, monthly
            period_map = {
                TimeFrame.DAILY: "daily",
                TimeFrame.WEEKLY: "weekly",
                TimeFrame.MONTHLY: "monthly"
            }
            ak_period = period_map.get(timeframe, "daily")
            
            df = await self.v1_provider.get_historical_data(
                symbol.code,
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
                period=ak_period
            )
            
            if df is None or df.empty:
                return []
                
            results = []
            for _, row in df.iterrows():
                try:
                    quote = StockDailyQuote(
                        symbol=symbol.code,
                        trade_date=row['date'].date() if isinstance(row['date'], datetime) else datetime.strptime(str(row['date']), "%Y-%m-%d").date(),
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=float(row['volume']),
                        amount=float(row.get('amount', 0.0)),
                        pct_chg=float(row.get('change_percent', 0.0)),
                        change=float(row.get('change', 0.0)),
                        pre_close=0.0, # Will be calculated or filled if needed
                        data_source=self.provider_name
                    )
                    results.append(quote)
                except Exception as e:
                    logger.warning(f"Error parsing AKShare row: {e}")
                    continue
            return results
        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            return []

    async def get_quote(self, symbol: SymbolKey) -> Optional[StockRealtimeQuote]:
        """获取实时行情"""
        try:
            data = await self.v1_provider.get_stock_quotes(symbol.code)
            if not data:
                return None
                
            return StockRealtimeQuote(
                symbol=symbol.code,
                name=data.get('name', ''),
                current_price=float(data.get('price', 0.0)),
                pre_close=float(data.get('pre_close', 0.0)),
                open=float(data.get('open', 0.0)),
                high=float(data.get('high', 0.0)),
                low=float(data.get('low', 0.0)),
                change=float(data.get('change', 0.0)),
                pct_chg=float(data.get('change_percent', 0.0)),
                volume=float(data.get('volume', 0.0)),
                amount=float(data.get('amount', 0.0)),
                timestamp=datetime.now(),
                data_source=self.provider_name
            )
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None

    async def get_basic_info(self, symbol: SymbolKey) -> Optional[StockBasicInfo]:
        """获取基础信息"""
        try:
            data = await self.v1_provider.get_stock_basic_info(symbol.code)
            if not data:
                return None
                
            return StockBasicInfo(
                symbol=symbol.code,
                exchange_symbol=data.get('full_symbol', symbol.code),
                name=data.get('name', ''),
                market=MarketType.CN.value,
                board="Main",
                industry=data.get('industry', 'Unknown'),
                sector=data.get('industry', 'Unknown'), # Use industry as sector if not available
                area=data.get('area', 'Unknown'),
                currency="CNY",
                data_source=self.provider_name
            )
        except Exception as e:
            logger.error(f"Failed to get basic info for {symbol}: {e}")
            return None

    async def get_news(self, symbol: SymbolKey, limit: int = 10, **kwargs) -> List[StockNews]:
        """获取新闻 (AKShare)"""
        try:
            # Determine market type for AKShare
            if symbol.market == MarketType.CN:
                # A股新闻
                news_list = await self.v1_provider.get_stock_news(symbol.code, limit)
                if not news_list:
                    return []
                
                result = []
                for item in news_list:
                    try:
                        # AKShare news item structure might be a dict, adapt to StockNews
                        publish_time = item.get('pub_date')
                        if isinstance(publish_time, str):
                            try:
                                publish_time = datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                publish_time = datetime.now() # Fallback if format is unexpected
                        elif not isinstance(publish_time, datetime):
                            publish_time = datetime.now()

                        stock_news = StockNews(
                            symbol=symbol.code,
                            title=item.get('title', ''),
                            content=item.get('content', ''),
                            url=item.get('url', ''),
                            source=item.get('source', 'AKShare'),
                            publish_time=publish_time,
                            category=NewsCategory.COMPANY_ANNOUNCEMENT, # Default category
                            data_source="akshare"
                        )
                        result.append(stock_news)
                    except Exception as e:
                        logger.warning(f"Error parsing AKShare news item: {e}")
                        continue
                return result
            elif symbol.market == MarketType.HK:
                # AKShare currently has limited direct HK stock news, return empty for now
                return []
            return []
        except Exception as e:
            logger.error(f"Failed to get news for {symbol}: {e}")
            return []

    async def get_sentiment(self, symbol: SymbolKey, **kwargs) -> str:
        """获取股票情绪分析数据 (中文市场)"""
        # 目前中文社交媒体情感分析使用占位符
        market_name = "中国A股" if symbol.market == MarketType.CN else "港股"
        curr_date = datetime.now().strftime("%Y-%m-%d")
        
        sentiment_summary = f"""## 中文市场情绪分析

**股票**: {symbol.code} ({market_name})
**分析日期**: {curr_date}

### 市场情绪概况
- 由于中文社交媒体情绪数据源暂未完全集成，当前提供基础分析
- 建议关注雪球、东方财富、同花顺等平台的讨论热度
- 港股市场还需关注香港本地财经媒体情绪

### 情绪指标
- 整体情绪: 中性
- 讨论热度: 待分析
- 投资者信心: 待评估

*注：完整的中文社交媒体情绪分析功能正在开发中*
"""
        return sentiment_summary

    async def get_symbol_list(self) -> List[SymbolKey]:
        """获取股票列表"""
        try:
            stocks = await self.v1_provider.get_stock_list()
            return [SymbolKey(market=MarketType.CN, code=s['code']) for s in stocks]
        except Exception as e:
            logger.error(f"Failed to get symbol list: {e}")
            return []

    async def search_symbol(self, query: str) -> List[SymbolKey]:
        """搜索股票"""
        try:
            stocks = await self.v1_provider.get_stock_list()
            results = []
            query_upper = query.upper()
            for s in stocks:
                if query_upper in s['code'].upper() or query_upper in s['name'].upper():
                    results.append(SymbolKey(market=MarketType.CN, code=s['code']))
            return results[:20] # Limit results
        except Exception as e:
            logger.error(f"Failed to search symbol: {e}")
            return []
