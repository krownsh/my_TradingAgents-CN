#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
會議室數據模型定義
定義多 Agent 協作過程中的消息、狀態與結構化報告
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class MessageRole(str, Enum):
    """會議角色"""
    MODERATOR = "moderator"      # 小韭菜 (主持人)
    TECHNICAL = "technical"      # 技術分析師
    FUNDAMENTAL = "fundamental"  # 基本面分析師
    SENTIMENT = "sentiment"      # 情緒分析師
    RISK = "risk"                # 風控專家
    DEBATER = "debater"          # 反方/質疑者
    USER = "user"                # 使用者 (老韭菜)

class MsgType(str, Enum):
    """消息類型"""
    OPENING = "opening"          # 開場白
    THINKING = "thinking"        # 思考過程
    OPINION = "opinion"          # 專家觀點
    TOOL_CALL = "tool_call"      # 工具調用
    TOOL_RESULT = "tool_result"  # 工具結果
    SUMMARY = "summary"          # 會議總結
    REPORT = "report"            # 結構化報告

class AgentMessage(BaseModel):
    """Agent 發言模型"""
    agent_id: str = Field(..., description="Agent 唯一標識")
    agent_name: str = Field(..., description="Agent 名稱")
    role: MessageRole = Field(..., description="Agent 角色")
    content: str = Field(..., description="發言內容")
    msg_type: MsgType = Field(default=MsgType.OPINION, description="消息類型")
    round: int = Field(default=1, description="會議輪次")
    timestamp: datetime = Field(default_factory=datetime.now)
    data_references: List[Dict[str, Any]] = Field(default_factory=list, description="引用數據")
    confidence: float = Field(default=1.0, description="置信度 (0-1)")

class MeetingContext(BaseModel):
    """會議上下文模型"""
    symbol_key: str = Field(..., description="股票標識 (e.g., US:AAPL)")
    query: str = Field(..., description="使用者問題")
    history: List[AgentMessage] = Field(default_factory=list, description="歷史發言")
    start_time: datetime = Field(default_factory=datetime.now)
    status: str = Field(default="init", description="會議狀態: init, gather, debate, synthesis, done")

class StructuredReport(BaseModel):
    """結構化分析報告"""
    symbol_key: str = Field(..., description="股票標識")
    title: str = Field(..., description="報告標題")
    thesis: str = Field(..., description="核心觀點/多空結論")
    bull_case: List[str] = Field(default_factory=list, description="利多因素")
    bear_case: List[str] = Field(default_factory=list, description="利空因素")
    risks: List[str] = Field(default_factory=list, description="潛在風險")
    assumptions: List[str] = Field(default_factory=list, description="分析假設")
    valuation_gap: Optional[str] = Field(None, description="估值偏差分析")
    target_price: Optional[Dict[str, Any]] = Field(None, description="目標價範圍/建議")
    conclusion: str = Field(..., description="總結陳詞")
    generated_at: datetime = Field(default_factory=datetime.now)

class MeetingEvent(BaseModel):
    """WebSocket 事件模型"""
    event_type: str = Field(..., description="事件類型: started, agent_thinking, tool_executed, message_received, finished")
    payload: Dict[str, Any] = Field(..., description="事件負載內容")
    timestamp: datetime = Field(default_factory=datetime.now)
