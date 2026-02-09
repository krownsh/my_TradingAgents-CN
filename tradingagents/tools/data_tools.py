#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料工具實現
將 DataFlowInterface 的功能封裝成註冊表工具
"""

import asyncio
from typing import List, Optional, Dict, Any
from tradingagents.dataflows.interface_v2 import get_dataflow_interface
from tradingagents.models.core import SymbolKey, MarketType, TimeFrame
from tradingagents.tools.registry import tool_registry

# 協助工具：處理非同步調用
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@tool_registry.register(
    name="market_quote",
    description="獲取股票即時報價，包括現價、漲跌幅、成交量等"
)
def get_market_quote(symbol_key: str) -> str:
    """獲取即時報價"""
    dfi = get_dataflow_interface()
    quote = run_async(dfi.get_quote(symbol_key))
    if not quote:
        return f"無法獲取 {symbol_key} 的報價"
    return str(quote.dict())

@tool_registry.register(
    name="market_bars",
    description="獲取股票歷史 K 線數據 (OHLCV)"
)
def get_market_bars(symbol_key: str, timeframe: str = "daily", limit: int = 30) -> str:
    """獲取 K 線"""
    dfi = get_dataflow_interface()
    # Map string timeframe to enum
    tf = TimeFrame.DAILY
    if timeframe.lower() == "weekly":
        tf = TimeFrame.WEEKLY
    
    bars = run_async(dfi.get_bars(symbol_key, timeframe=tf, limit=limit))
    if not bars:
        return f"無法獲取 {symbol_key} 的歷史數據"
    
    return "\n".join([str(b.dict()) for b in bars])

@tool_registry.register(
    name="market_news",
    description="獲取與股票相關的最新新聞報導"
)
def get_market_news(symbol_key: str, limit: int = 5) -> str:
    """獲取新聞"""
    dfi = get_dataflow_interface()
    # Need SymbolKey object for get_news in v2
    sk = dfi._ensure_symbol_key(symbol_key)
    news_list = run_async(dfi.get_news(sk, limit=limit))
    if not news_list:
        return f"目前沒有 {symbol_key} 的相關新聞"
    
    res = []
    for n in news_list:
        res.append(f"標題: {n.title}\n來源: {n.source}\n時間: {n.publish_time}\n內容摘要: {n.summary or n.content[:200]}")
    return "\n---\n".join(res)

@tool_registry.register(
    name="market_sentiment",
    description="獲取市場對該股票的輿情情緒分析（包括社交媒體與新聞情緒）"
)
def get_market_sentiment(symbol_key: str) -> str:
    """獲取情緒節報"""
    dfi = get_dataflow_interface()
    sk = dfi._ensure_symbol_key(symbol_key)
    sentiment = run_async(dfi.get_sentiment(sk))
    return sentiment
