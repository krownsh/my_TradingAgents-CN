import logging
from typing import Optional, List, Union, Dict, Any
from datetime import datetime, timedelta

from tradingagents.models.core import SymbolKey, MarketType, TimeFrame, AssetType
from tradingagents.models.stock_data_models import StockDailyQuote, StockRealtimeQuote, StockNews, StockBasicInfo
from tradingagents.providers.manager import ProviderManager
from tradingagents.providers.us.yahoo import YahooFinanceProvider
from tradingagents.providers.tw.twse import TWSEProvider
from tradingagents.providers.tw.tpex import TPExProvider
from tradingagents.providers.china.akshare import AKShareDataProviderV2

logger = logging.getLogger(__name__)

class DataFlowInterface:
    """
    DataFlow V2 统一接口 (Market-Aware)
    取代旧的 interface.py，使用 ProviderManager 进行数据获取。
    """

    def __init__(self):
        self.provider_manager = ProviderManager()
        self._init_providers()

    def _init_providers(self):
        """初始化默认 Providers"""
        # MVP: Register known providers
        # 实际生产中可能从配置读取
        self.provider_manager.register_provider(YahooFinanceProvider())
        self.provider_manager.register_provider(TWSEProvider())
        self.provider_manager.register_provider(TPExProvider())
        self.provider_manager.register_provider(AKShareDataProviderV2())
        logger.info("DataFlowInterface initialized with default providers.")

    async def get_bars(
        self, 
        symbol: Union[SymbolKey, str], 
        timeframe: TimeFrame = TimeFrame.DAILY,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[StockDailyQuote]:
        """
        获取K线数据
        优先从 MongoDB 缓存获取，如果不存在则从 Provider 获取。
        
        Args:
            symbol: SymbolKey 对象或 字符串代码
            timeframe: 时间周期
            start_date: 开始时间
            end_date: 结束时间
            limit: 如果未指定时间范围，返回最近 N 条
        """
        # Convert string to SymbolKey if needed (Best Effort)
        target_symbol = self._ensure_symbol_key(symbol)
        
        # Default dates
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            # Default to some reasonable window if limit is not strictly used by providers yet
            start_date = end_date - timedelta(days=limit * 2) # Rough estimate for daily
            
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # 1. Try Cache (MongoDB)
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import get_mongodb_cache_adapter
            cache_adapter = get_mongodb_cache_adapter()
            
            # cache_adapter.get_historical_data accepts SymbolKey now
            df = cache_adapter.get_historical_data(
                target_symbol, 
                start_date=start_str, 
                end_date=end_str, 
                period=timeframe.value if isinstance(timeframe, TimeFrame) else timeframe
            )
            
            if df is not None and not df.empty:
                logger.info(f"📊 [DataFlow] Cache hit for {target_symbol}")
                # Convert DataFrame to List[StockDailyQuote]
                # Note: DataFrame columns should match model fields
                quotes = []
                for _, row in df.iterrows():
                    # Handle potential date format differences in DF
                    d = row.to_dict()
                    # Ensure minimal required fields for StockDailyQuote
                    # If conversion fails, we might fallback
                    try:
                        quotes.append(StockDailyQuote(**d))
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to convert cached row to StockDailyQuote: {e}")
                if quotes:
                    return quotes
        except Exception as e:
            logger.warning(f"⚠️ Cache lookup failed: {e}")

        # 2. Fallback to Provider
        logger.info(f"🔄 [DataFlow] Cache miss for {target_symbol}, fetching from provider...")
        return await self.provider_manager.get_bars(target_symbol, timeframe, start_date, end_date)

    async def get_quote(self, symbol: Union[SymbolKey, str]) -> Optional[StockRealtimeQuote]:
        """获取实时行情"""
        target_symbol = self._ensure_symbol_key(symbol)
        return await self.provider_manager.get_quote(target_symbol)

    async def get_basic_info(self, symbol: Union[SymbolKey, str]) -> Optional[StockBasicInfo]:
        """获取基础信息"""
        target_symbol = self._ensure_symbol_key(symbol)
        return await self.provider_manager.get_basic_info(target_symbol)

    async def get_news(self, symbol: SymbolKey, limit: int = 10, **kwargs) -> List[StockNews]:
        """获取新闻数据"""
        return await self.provider_manager.get_news(symbol, limit=limit, **kwargs)

    async def get_sentiment(self, symbol: SymbolKey, **kwargs) -> str:
        """获取股票情绪分析数据"""
        return await self.provider_manager.get_sentiment(symbol, **kwargs)

    def _ensure_symbol_key(self, symbol: Union[SymbolKey, str]) -> SymbolKey:
        """
        Helper: Ensure we have a SymbolKey.
        If string is provided, try to guess.
        """
        if isinstance(symbol, SymbolKey):
            return symbol
        
        # Simple heuristics for MVP
        s = str(symbol).upper()
        if s.isdigit():
            if len(s) == 6:
                return SymbolKey(market=MarketType.CN, code=s)
            elif len(s) == 4:
                # Default to TW for 4 digits in this context? Or HK?
                # Let's assume TW for now as it's a focus
                return SymbolKey(market=MarketType.TW, code=s)
        
        # Assume US if letters
        return SymbolKey(market=MarketType.US, code=s)

# Global Instance
_data_flow_interface = None

def get_dataflow_interface() -> DataFlowInterface:
    global _data_flow_interface
    if not _data_flow_interface:
        _data_flow_interface = DataFlowInterface()
    return _data_flow_interface
