#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
會議編排器 (Orchestrator)
負責控制會議流程、調用專家、管理歷史記錄與工具執行
"""

import asyncio
import logging
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime

from .schemas import AgentMessage, MessageRole, MsgType, MeetingContext, MeetingEvent, StructuredReport
from .moderator import Moderator
from tradingagents.tools.registry import tool_registry

logger = logging.getLogger(__name__)

class MeetingOrchestrator:
    """會議室的核心引擎"""
    
    def __init__(self, llm_factory: Callable):
        self.llm_factory = llm_factory
        self.moderator = Moderator(llm_factory("moderator"))
        self.agents: Dict[str, Any] = {} # 暫存本次會議的專家實例

    async def run_meeting(
        self, 
        symbol_key: str, 
        query: str, 
        event_callback: Optional[Callable[[MeetingEvent], None]] = None
    ) -> StructuredReport:
        """運行完整的會議流程"""
        ctx = MeetingContext(symbol_key=symbol_key, query=query)
        
        async def emit(event_type: str, payload: Dict[str, Any]):
            if event_callback:
                event = MeetingEvent(event_type=event_type, payload=payload)
                if asyncio.iscoroutinefunction(event_callback):
                    await event_callback(event)
                else:
                    event_callback(event)

        # 1. 分析意圖
        await emit("status", {"message": "正在分析您的需求..."})
        decision = await self.moderator.analyze_intent(query, symbol_key)
        selected_roles = decision.get("selected_agents", ["technical", "fundamental"])
        
        # 2. 開場白
        await emit("status", {"message": "小韭菜進入會議室..."})
        opening = await self.moderator.generate_opening(ctx)
        ctx.history.append(opening)
        await emit("message", opening.dict())

        # 3. 專家發言 (串行討論)
        for role_name in selected_roles:
            await emit("status", {"message": f"請專家 {role_name} 發表意見..."})
            agent_msg = await self._run_expert(role_name, ctx, emit)
            ctx.history.append(agent_msg)
            await emit("message", agent_msg.dict())

        # 4. 總結
        await emit("status", {"message": "正在生成總結報告..."})
        report = await self.moderator.synthesize(ctx)
        await emit("report", report.dict())
        await emit("finished", {"message": "會議結束"})
        
        return report

    async def _run_expert(self, role: str, ctx: MeetingContext, emit_f: Callable) -> AgentMessage:
        """執行單個專家"""
        llm = self.llm_factory(role)
        
        # 建立專家 System Prompt
        history_summary = "\n".join([f"[{m.agent_name}]: {m.content}" for m in ctx.history])
        
        system_prompt = f"""
        你是一位專業的股票分析師，角色為: {role}。
        你正在參加一場關於 {ctx.symbol_key} 的研討會。
        目前討論的主題是: {ctx.query}
        
        之前的討論記錄如下:
        {history_summary}
        
        請在遵守你的專業立場下，提出你的見解。
        你可以使用以下工具來獲取最新數據:
        {tool_registry.get_tool_schemas()}
        
        你需要先思考 (Thinking)，然後決定是否調用工具，最後給出結論。
        """
        
        # 這裡簡化為一次性 Invoke，實際應支持 Tool Calling 循環
        # 整合 ToolRegistry 的邏輯
        response = await llm.ainvoke(system_prompt)
        content = response.content
        
        return AgentMessage(
            agent_id=role,
            agent_name=f"{role.capitalize()} Analyst",
            role=MessageRole(role),
            content=content,
            msg_type=MsgType.OPINION
        )
