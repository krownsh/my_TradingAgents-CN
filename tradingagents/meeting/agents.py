#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
專家 Agent 實現
定義技術、基本面、輿情與風控分析師的角色行為
"""

import logging
from typing import List, Dict, Any, Optional
from .schemas import AgentMessage, MessageRole, MsgType, MeetingContext
from tradingagents.tools.registry import tool_registry

logger = logging.getLogger(__name__)

class ExpertAgent:
    """通用專家 Agent"""
    
    def __init__(self, role: MessageRole, name: str, llm):
        self.role = role
        self.name = name
        self.llm = llm

    async def speak(self, ctx: MeetingContext) -> AgentMessage:
        """發表意見"""
        # 獲取歷史摘要
        history_text = "\n".join([f"[{m.agent_name}]: {m.content}" for m in ctx.history])
        
        system_prompt = self._get_system_prompt(ctx.symbol_key, history_text)
        
        # 這裡調用 LLM
        # 實務上應包含 Tool Calling 循環，此處為 MVP 演示簡化版
        response = await self.llm.ainvoke(system_prompt)
        
        return AgentMessage(
            agent_id=self.role.value,
            agent_name=self.name,
            role=self.role,
            content=response.content,
            msg_type=MsgType.OPINION
        )

    def _get_system_prompt(self, symbol_key: str, history: str) -> str:
        base = f"""
        你是一位專業的股票分析師，角色為: {self.name} ({self.role.value})。
        目前分析對象: {symbol_key}。
        
        會議歷史記錄:
        {history}
        
        請基於你的專業背景發表對該股票的看法。
        如果需要數據，請聲明你需要調用哪些工具。
        """
        
        role_specific = {
            MessageRole.TECHNICAL: "專注於 K 線形態、均線、量價關係與技術指標 (MACD/RSI/BOLL)。",
            MessageRole.FUNDAMENTAL: "專注於營收增長、獲利能力、資產負債狀況與產業競爭力。",
            MessageRole.SENTIMENT: "專注於新聞熱度、社群情緒、法人進出與市場氛圍。",
            MessageRole.RISK: "專注於潛在的利空風險、政策不確定性與黑天鵝因素。"
        }
        
        return base + role_specific.get(self.role, "")
