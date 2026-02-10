#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研究數據模型 (Research Models)
定義 Dexter 研究 Agent 的相關數據結構
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from .core import SymbolKey, MarketType

class ResearchEvent(BaseModel):
    """
    研究事件模型 (Research Event)
    記錄單次工具調用及其結果
    """
    event_id: str = Field(..., description="唯一事件 ID (通常是 step_id)")
    plan_id: int = Field(..., description="所屬計畫 ID")
    symbol_key: str = Field(..., description="標的鍵值")
    tool_name: str = Field(..., description="使用的工具名稱")
    args: Dict[str, Any] = Field(default_factory=dict, description="工具調用參數")
    
    # 結果數據
    data: Any = Field(None, description="工具返回的原始數據")
    quality: int = Field(default=0, description="結果品質評分 (0-100)")
    source_provider: str = Field(..., description="數據來源提供者")
    message: Optional[str] = Field(None, description="補充信息或錯誤訊息")
    
    # 時間戳
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 關聯
    requester: Optional[str] = Field(None, description="請求者 (如專家角色)")
    trigger_reason: str = Field(default="initial", description="觸發原因")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ResearchSessionSummary(BaseModel):
    """
    研究會話摘要
    """
    session_id: str = Field(..., description="會話 ID (通常是 meeting_id)")
    symbol_key: str = Field(..., description="標的鍵值")
    query: str = Field(..., description="原始查詢內容")
    plans: List[Dict[str, Any]] = Field(default_factory=list, description="計畫歷史")
    total_tools_called: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
