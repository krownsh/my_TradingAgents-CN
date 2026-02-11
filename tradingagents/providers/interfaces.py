from abc import ABC, abstractmethod
from typing import List, Optional, Union, Dict, Any
from datetime import datetime, date

from tradingagents.models.core import SymbolKey, TimeFrame, MarketType
from tradingagents.models.stock_data_models import StockDailyQuote, StockBasicInfo, StockRealtimeQuote, StockNews

class MarketDataProvider(ABC):
    """
    市场数据提供者抽象基类 (Market Data Provider Abstract Base Class)
    定义所有数据源必须实现的统一接口。
    """
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    @abstractmethod
    async def connect(self) -> bool:
        """建立连接 (如需要)"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    async def search_symbol(self, query: str) -> List[SymbolKey]:
        """
        搜寻标的
        
        Args:
            query: 搜寻关键字 (代码, 名称等)
            
        Returns:
            符合条件的 SymbolKey 列表
        """
        pass

    @abstractmethod
    async def get_symbol_list(self) -> List[SymbolKey]:
        """
        获取该市场所有标的列表
        
        Returns:
            SymbolKey 列表
        """
        pass

    @abstractmethod
    async def get_quote(self, symbol: SymbolKey) -> Optional[StockRealtimeQuote]:
        """
        获取实时/延迟行情 (Quote)
        
        Args:
            symbol: 标的键值
            
        Returns:
            最新行情数据
        """
        pass

    @abstractmethod
    async def get_bars(
        self, 
        symbol: SymbolKey, 
        timeframe: TimeFrame, 
        start: datetime, 
        end: datetime
    ) -> List[StockDailyQuote]:
        """
        获取历史K线数据 (Bars)
        
        Args:
            symbol: 标的键值
            timeframe: 时间周期
            start: 开始时间
            end: 结束时间
            
        Returns:
            K线数据列表
        """
        pass

    @abstractmethod
    async def get_basic_info(self, symbol: SymbolKey) -> Optional[StockBasicInfo]:
        """
        获取标的基础信息 (Basic Info)
        
        Args:
            symbol: 标的键值
            
        Returns:
            基础信息对象
        """
        pass

    @abstractmethod
    async def get_news(self, symbol: SymbolKey) -> List[StockNews]:
        """
        获取相关新闻

        Returns:
            新闻列表
        """
        return []

    @property
    @abstractmethod
    def supported_markets(self) -> List[MarketType]:
        """支持的市场列表"""
        pass
