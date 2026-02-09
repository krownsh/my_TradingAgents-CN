import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from tradingagents.models.core import SymbolKey, TimeFrame, MarketType
from tradingagents.models.stock_data_models import StockDailyQuote, StockBasicInfo, StockRealtimeQuote, StockNews
from tradingagents.providers.interfaces import MarketDataProvider

logger = logging.getLogger(__name__)

class ProviderManager:
    """
    数据源管理器 (Provider Manager)
    负责管理不同市场的 Data Provider，并处理 Request Routing 与 Fallback 机制。
    替代旧有的 DataSourceManager。
    """

    def __init__(self):
        # 存储各市场的 Provider 列表 (按优先级排序)
        self.providers: Dict[MarketType, List[MarketDataProvider]] = {}
        self._initialized = False

    def register_provider(self, provider: MarketDataProvider):
        """
        注册 Provider
        
        Args:
            provider: 实现了 MarketDataProvider 的实例
        """
        for market in provider.supported_markets:
            if market not in self.providers:
                self.providers[market] = []
            
            # 目前简单的 append，后续可加入优先级权重排序
            self.providers[market].append(provider)
            logger.info(f"Registered provider {provider.provider_name} for market {market.value}")

    async def get_bars(
        self, 
        symbol: SymbolKey, 
        timeframe: TimeFrame, 
        start: datetime, 
        end: datetime
    ) -> List[StockDailyQuote]:
        """
        获取历史K线数据 (自动路由与降级)
        """
        providers = self._get_providers_for_market(symbol.market)
        
        last_error = None
        for provider in providers:
            try:
                # 尝试从 Provider 获取数据
                data = await provider.get_bars(symbol, timeframe, start, end)
                if data:
                    return data
            except Exception as e:
                logger.warning(f"Provider {provider.provider_name} failed to get bars for {symbol.code}: {e}")
                last_error = e
                continue
        
        if last_error:
            raise last_error
        return []

    async def get_quote(self, symbol: SymbolKey) -> Optional[StockRealtimeQuote]:
        """
        获取实时行情 (自动路由与降级)
        """
        providers = self._get_providers_for_market(symbol.market)
        
        for provider in providers:
            try:
                data = await provider.get_quote(symbol)
                if data:
                    return data
            except Exception as e:
                logger.warning(f"Provider {provider.provider_name} failed to get quote for {symbol.code}: {e}")
                continue
        
        return None

    async def get_basic_info(self, symbol: SymbolKey) -> Optional[StockBasicInfo]:
        """
        获取基础信息 (自动路由与降级)
        """
        providers = self._get_providers_for_market(symbol.market)
        
        for provider in providers:
            try:
                data = await provider.get_basic_info(symbol)
                if data:
                    return data
            except Exception as e:
                logger.warning(f"Provider {provider.provider_name} failed to get basic info for {symbol.code}: {e}")
                continue
        
        return None

        
        return []

    async def search_symbol(self, query: str, market: MarketType = None) -> List[SymbolKey]:
        """
        搜索标的
        
        Args:
            query: 搜索关键字
            market: 指定搜索市场 (可选)
            
        Returns:
            搜索结果列表
        """
        results = []
        
        # 确定要搜索的市场范围
        target_markets = [market] if market else list(self.providers.keys())
        
        for m in target_markets:
            providers = self._get_providers_for_market(m)
            for provider in providers:
                try:
                    # 搜索并合并结果
                    res = await provider.search_symbol(query)
                    if res:
                        results.extend(res)
                        # 如果找到结果，是否继续搜寻其他 Provider 取决于策略，这里简单地全部搜寻
                except Exception as e:
                    logger.warning(f"Provider {provider.provider_name} search failed: {e}")
        
        # 去重 (根据 SymbolKey 的 hash)
        return list(set(results))

    def _get_providers_for_market(self, market: MarketType) -> List[MarketDataProvider]:
        """获取指定市场的 Provider 列表"""
        return self.providers.get(market, [])
