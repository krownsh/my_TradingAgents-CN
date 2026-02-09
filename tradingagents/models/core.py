#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心数据模型 (Core Data Models)
定义系统中最基础的数据结构，如 SymbolKey, MarketType 等。
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class MarketType(str, Enum):
    """市场类型枚举"""
    CN = "CN"  # 中国A股
    HK = "HK"  # 港股
    US = "US"  # 美股
    TW = "TW"  # 台湾股市


class AssetType(str, Enum):
    """资产类型枚举"""
    EQUITY = "EQUITY"    # 股票
    INDEX = "INDEX"      # 指数
    ETF = "ETF"          # ETF
    FUTURES = "FUTURES"  # 期货
    OPTION = "OPTION"    # 期权
    FOREX = "FOREX"      # 外汇
    CRYPTO = "CRYPTO"    # 加密货币


class TimeFrame(str, Enum):
    """时间周期枚举"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    MINUTE_60 = "60m"
    DAILY = "1d"
    WEEKLY = "1wk"
    MONTHLY = "1mo"


class SymbolKey(BaseModel):
    """
    统一的标的键值 (Symbol Key)
    用于在系统中唯一标识一个交易标的。
    """
    market: MarketType = Field(..., description="市场类型")
    exchange: Optional[str] = Field(None, description="交易所代码 (如 NYSE, TWSE, SSE)")
    code: str = Field(..., description="标的代码 (如 AAPL, 2330, 600519)")
    asset_type: AssetType = Field(default=AssetType.EQUITY, description="资产类型")

    class Config:
        use_enum_values = True
        json_encoders = {
            MarketType: lambda v: v.value,
            AssetType: lambda v: v.value
        }

    def __str__(self):
        market_val = self.market.value if hasattr(self.market, 'value') else self.market
        return f"{market_val}:{self.code}"

    def __hash__(self):
        return hash(str(self))
