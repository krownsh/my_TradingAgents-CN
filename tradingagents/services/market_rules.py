from typing import Dict, Any, Optional
from datetime import time, datetime
from tradingagents.models.core import MarketType, SymbolKey

class MarketRulesService:
    """
    市场规则服务 (Market Rules Service)
    提供各市场的交易规则，如交易时间、涨跌幅限制、交易单位等。
    """

    @staticmethod
    def get_market_timezone(market: MarketType) -> str:
        """获取市场时区"""
        if market == MarketType.TW:
            return "Asia/Taipei"
        elif market in [MarketType.CN, MarketType.HK]:
            return "Asia/Shanghai"  # CN/HK (GMT+8)
        elif market == MarketType.US:
            return "America/New_York"
        return "UTC"

    @staticmethod
    def get_currency(market: MarketType) -> str:
        """获取市场货币代号"""
        if market == MarketType.TW:
            return "TWD"
        elif market == MarketType.US:
            return "USD"
        elif market == MarketType.CN:
            return "CNY"
        elif market == MarketType.HK:
            return "HKD"
        return "USD"

    @staticmethod
    def get_trading_hours(market: MarketType) -> Dict[str, time]:
        """
        获取交易时间 (本地时间)
        """
        if market == MarketType.TW:
            return {
                "pre_open": time(8, 30),
                "open": time(9, 0),
                "close": time(13, 30),
                "post_close_starts": time(13, 30),
                "post_close_ends": time(14, 30) # 盘后定价交易
            }
        elif market == MarketType.US:
            return {
                "pre_market_start": time(4, 0),
                "open": time(9, 30),
                "close": time(16, 0),
                "after_hours_end": time(20, 0)
            }
        # Default fallback
        return {"open": time(9, 0), "close": time(15, 0)}

    @staticmethod
    def is_market_open(market: MarketType, current_time: datetime = None) -> bool:
        """
        判断市场当前是否开盘 (简单略估，未考虑假日)
        TODO: 集成交易日历服务
        """
        # 这是一个占位实现，实际需要结合 CalendarService
        return True

    @staticmethod
    def get_lot_size(symbol: SymbolKey) -> int:
        """
        获取最小交易单位 (股数)
        """
        if symbol.market == MarketType.TW:
            return 1000 # 台股一般是1000股 (零股除外)
        elif symbol.market == MarketType.CN:
            return 100 # A股是100股
        elif symbol.market == MarketType.US:
            return 1 # 美股是1股
        return 1
    
    @staticmethod
    def get_price_limit_ratio(symbol: SymbolKey) -> float:
        """
        获取涨跌幅限制比例 (0.10 = 10%)
        """
        if symbol.market == MarketType.TW:
            return 0.10 # 10%
        elif symbol.market == MarketType.CN:
            # 简单处理，未区分科创板/创业板 (20%)
            return 0.10 
        elif symbol.market == MarketType.US:
            return 0.0 # 无限制
        return 0.0
