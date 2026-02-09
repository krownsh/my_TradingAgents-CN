#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主持人 (Moderator) - 小韭菜
負責分析用戶意圖、選擇專家、引導討論與最終總結
"""

import json
import logging
from typing import List, Dict, Any, Optional
from .schemas import AgentMessage, MessageRole, MsgType, MeetingContext, StructuredReport

logger = logging.getLogger(__name__)

class Moderator:
    """小韭菜主持人"""
    
    def __init__(self, llm):
        self.llm = llm
        self.role = MessageRole.MODERATOR
        self.name = "小韭菜"

    async def analyze_intent(self, query: str, symbol_key: str) -> Dict[str, Any]:
        """
        分析用戶意圖並選擇專家
        回傳結構: { "selected_agents": ["technical", "fundamental"], "discussion_topic": "..." }
        """
        prompt = f"""
        你是一位專業的股票研究中心主持人「小韭菜」。
        用戶的問題是: "{query}"
        目標股票: {symbol_key}

        請根據問題，從以下專家庫中選擇最合適的 1-3 位專家進行討論：
        1. technical: 技術分析專家，擅長 K 線、指標、趨勢。
        2. fundamental: 基本面專家，擅長財報、估值、產業競爭力。
        3. sentiment: 情緒分析專家，擅長新聞、社群輿情。
        4. risk: 風控專家，擅長挖掘隱含波定性與利空風險。

        請以 JSON 格式回覆，包含:
        - selected_agents: 選中的專家角色列表
        - discussion_topic: 本次討論的核心議題
        - reason: 選擇理由
        """
        
        response = await self.llm.ainvoke(prompt)
        content = response.content
        
        # 簡單的 JSON 提取邏輯
        try:
            # 尋找 JSON 區塊
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                data = json.loads(content[start:end])
                return data
            return {"selected_agents": ["technical", "fundamental"], "discussion_topic": query}
        except Exception as e:
            logger.error(f"解析 Moderator 意圖失敗: {e}")
            return {"selected_agents": ["technical", "fundamental"], "discussion_topic": query}

    async def generate_opening(self, ctx: MeetingContext) -> AgentMessage:
        """生成開場白"""
        prompt = f"""
        你是研究中心主持人「小韭菜」。
        本次討論股票: {ctx.symbol_key}
        核心議題: {ctx.query}
        
        請用親切、專業且略帶幽默的語氣開場，介紹即將發言的專家。
        """
        response = await self.llm.ainvoke(prompt)
        return AgentMessage(
            agent_id="moderator",
            agent_name=self.name,
            role=self.role,
            content=response.content,
            msg_type=MsgType.OPENING
        )

    async def synthesize(self, ctx: MeetingContext) -> StructuredReport:
        """生成最終結構化報告"""
        # 收集所有討論歷史
        history_text = "\n".join([f"[{m.agent_name}]: {m.content}" for m in ctx.history])
        
        prompt = f"""
        你是研究中心主持人「小韭菜」。請根據以下討論記錄，為 {ctx.symbol_key} 生成一份結構化的投資研究摘要。
        
        討論記錄:
        {history_text}
        
        請按以下 JSON 格式輸出：
        {{
            "title": "股票分析報告",
            "thesis": "多空結論 (一句話)",
            "bull_case": ["利多1", "利多2"],
            "bear_case": ["利空1", "利空2"],
            "risks": ["風險1"],
            "conclusion": "最終建議"
        }}
        """
        response = await self.llm.ainvoke(prompt)
        content = response.content
        
        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            data = json.loads(content[start:end])
            return StructuredReport(symbol_key=ctx.symbol_key, **data)
        except Exception as e:
            logger.error(f"生成結構化報告失敗: {e}")
            return StructuredReport(
                symbol_key=ctx.symbol_key,
                title="分析報告 (解析失敗)",
                thesis="未知",
                conclusion="解析總結失敗，請查閱對話記錄。"
            )
