"""
Dexter Adapter - 工具適配層

將 Dexter 的財務工具介面適配到 TradingAgents-CN 的 Provider 系統。
支援 US + TW 雙市場。
"""

__version__ = "0.1.0"

from .scratchpad import DexterScratchpad

__all__ = ["DexterScratchpad"]
