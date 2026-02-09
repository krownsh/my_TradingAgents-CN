"""
Fundamentals Adapter - 財報數據適配器

將 Dexter 的財報查詢需求適配到 TradingAgents-CN 的financial 系統。
US 市場支援完整財報，TW 市場回傳 MISSING fallback。
"""

from datetime import datetime
from typing import Literal, Optional
import logging

from tradingagents.dexter_adapter.schemas import DexterToolOutput
from tradingagents.dataflows.interface_v2 import DataFlowInterface

logger = logging.getLogger(__name__)


async def dexter_get_income_statement(
    symbol_key: str,
    period: Literal["annual", "quarterly"] = "annual",
    limit: int = 5
) -> DexterToolOutput:
    """
    獲取損益表（Income Statement）
    
    對應 Dexter 的 getIncomeStatements。
    目前僅支援 US 市場，TW 市場回傳 MISSING + 建議替代方案。
    
    Args:
        symbol_key: 標準化格式，如 'US:AAPL'
        period: 財報週期，'annual' 或 'quarterly'
        limit: 返回筆數，預設 5
        
    Returns:
        DexterToolOutput: 包含損益表資料或 MISSING 說明
    """
    try:
        market, symbol = symbol_key.split(':', 1)
        
        # TW 市場：財報未標準化，回傳 MISSING
        if market == "TW":
            return DexterToolOutput(
                data=None,
                quality="MISSING",
                source_provider="mops",
                asof=datetime.utcnow(),
                market=market,
                symbol=symbol,
                message=(
                    "台股完整損益表尚未支援（MOPS 資料未標準化）。"
                    "建議使用：\n"
                    "1. 月營收資料（較即時）\n"
                    "2. MOPS 公告（關鍵事件）\n"
                    "3. 基本指標（如本益比、ROE）"
                )
            )
        
        # US 市場：使用 DataFlowInterface
        if market == "US":
            interface = DataFlowInterface()
            
            try:
                financials = await interface.get_fundamentals(
                    symbol=symbol,
                    market=market,
                    statement_type="income_statement",
                    period=period,
                    limit=limit
                )
                
                if not financials or not financials.get("data"):
                    return DexterToolOutput(
                        data=None,
                        quality="MISSING",
                        source_provider="fundamentals",
                        asof=datetime.utcnow(),
                        market=market,
                        symbol=symbol,
                        message=f"無法獲取 {symbol_key} 的損益表"
                    )
                
                return DexterToolOutput(
                    data=financials.get("data"),
                    quality="EOD",
                    source_provider=financials.get("provider", "fundamentals"),
                    asof=datetime.utcnow(),
                    market=market,
                    symbol=symbol,
                    source_urls=financials.get("source_urls", [])
                )
            except Exception as e:
                logger.error(f"Error fetching income statement for {symbol_key}: {e}")
                return DexterToolOutput(
                    data=None,
                    quality="MISSING",
                    source_provider="error",
                    asof=datetime.utcnow(),
                    market=market,
                    symbol=symbol,
                    message=f"獲取損益表失敗: {str(e)}"
                )
        
        # 其他市場：暫不支援
        return DexterToolOutput(
            data=None,
            quality="MISSING",
            source_provider="unknown",
            asof=datetime.utcnow(),
            market=market,
            symbol=symbol,
            message=f"市場 {market} 暫不支援財報查詢"
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


async def dexter_get_balance_sheet(
    symbol_key: str,
    period: Literal["annual", "quarterly"] = "annual",
    limit: int = 5
) -> DexterToolOutput:
    """獲取資產負債表（Balance Sheet）"""
    try:
        market, symbol = symbol_key.split(':', 1)
        
        if market == "TW":
            return DexterToolOutput(
                data=None,
                quality="MISSING",
                source_provider="mops",
                asof=datetime.utcnow(),
                market=market,
                symbol=symbol,
                message="台股完整資產負債表尚未支援"
            )
        
        if market == "US":
            interface = DataFlowInterface()
            
            try:
                financials = await interface.get_fundamentals(
                    symbol=symbol,
                    market=market,
                    statement_type="balance_sheet",
                    period=period,
                    limit=limit
                )
                
                if not financials or not financials.get("data"):
                    return DexterToolOutput(
                        data=None,
                        quality="MISSING",
                        source_provider="fundamentals",
                        asof=datetime.utcnow(),
                        market=market,
                        symbol=symbol,
                        message=f"無法獲取 {symbol_key} 的資產負債表"
                    )
                
                return DexterToolOutput(
                    data=financials.get("data"),
                    quality="EOD",
                    source_provider=financials.get("provider", "fundamentals"),
                    asof=datetime.utcnow(),
                    market=market,
                    symbol=symbol,
                    source_urls=financials.get("source_urls", [])
                )
            except Exception as e:
                logger.error(f"Error fetching balance sheet for {symbol_key}: {e}")
                return DexterToolOutput(
                    data=None,
                    quality="MISSING",
                    source_provider="error",
                    asof=datetime.utcnow(),
                    market=market,
                    symbol=symbol,
                    message=f"獲取資產負債表失敗: {str(e)}"
                )
        
        return DexterToolOutput(
            data=None,
            quality="MISSING",
            source_provider="unknown",
            asof=datetime.utcnow(),
            market=market,
            symbol=symbol,
            message=f"市場 {market} 暫不支援財報查詢"
        )
        
    except ValueError as e:
        return DexterToolOutput(
            data=None,
            quality="MISSING",
            source_provider="error",
            asof=datetime.utcnow(),
            message=f"symbol_key 格式錯誤: {str(e)}"
        )


async def dexter_get_cash_flow(
    symbol_key: str,
    period: Literal["annual", "quarterly"] = "annual",
    limit: int = 5
) -> DexterToolOutput:
    """獲取現金流量表（Cash Flow Statement）"""
    try:
        market, symbol = symbol_key.split(':', 1)
        
        if market == "TW":
            return DexterToolOutput(
                data=None,
                quality="MISSING",
                source_provider="mops",
                asof=datetime.utcnow(),
                market=market,
                symbol=symbol,
                message="台股完整現金流量表尚未支援"
            )
        
        if market == "US":
            interface = DataFlowInterface()
            
            try:
                financials = await interface.get_fundamentals(
                    symbol=symbol,
                    market=market,
                    statement_type="cash_flow",
                    period=period,
                    limit=limit
                )
                
                if not financials or not financials.get("data"):
                    return DexterToolOutput(
                        data=None,
                        quality="MISSING",
                        source_provider="fundamentals",
                        asof=datetime.utcnow(),
                        market=market,
                        symbol=symbol,
                        message=f"無法獲取 {symbol_key} 的現金流量表"
                    )
                
                return DexterToolOutput(
                    data=financials.get("data"),
                    quality="EOD",
                    source_provider=financials.get("provider", "fundamentals"),
                    asof=datetime.utcnow(),
                    market=market,
                    symbol=symbol,
                    source_urls=financials.get("source_urls", [])
                )
            except Exception as e:
                logger.error(f"Error fetching cash flow for {symbol_key}: {e}")
                return DexterToolOutput(
                    data=None,
                    quality="MISSING",
                    source_provider="error",
                    asof=datetime.utcnow(),
                    market=market,
                    symbol=symbol,
                    message=f"獲取現金流量表失敗: {str(e)}"
                )
        
        return DexterToolOutput(
            data=None,
            quality="MISSING",
            source_provider="unknown",
            asof=datetime.utcnow(),
            market=market,
            symbol=symbol,
            message=f"市場 {market} 暫不支援財報查詢"
        )
        
    except ValueError as e:
        return DexterToolOutput(
            data=None,
            quality="MISSING",
            source_provider="error",
            asof=datetime.utcnow(),
            message=f"symbol_key 格式錯誤: {str(e)}"
        )
