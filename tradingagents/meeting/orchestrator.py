#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
會議編排器 (Orchestrator)
負責控制會議流程、調用專家、管理歷史記錄與工具執行
整合 Dexter PLAN state + Scratchpad + 動態規劃
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Callable, Optional, Tuple
from datetime import datetime

from .schemas import AgentMessage, MessageRole, MsgType, MeetingContext, MeetingEvent, StructuredReport
from .moderator import Moderator
from .states import MeetingState
from tradingagents.tools.registry import tool_registry
from tradingagents.dexter_adapter.planner import DexterPlanner
from tradingagents.dexter_adapter.schemas import ResearchPlan
from tradingagents.dexter_adapter.scratchpad import DexterScratchpad
from tradingagents.dexter_adapter import tools as dexter_tools

logger = logging.getLogger(__name__)

class MeetingOrchestrator:
    """會議室的核心引擎（整合 Dexter PLAN state + 動態規劃）"""
    
    def __init__(self, llm_factory: Callable, max_discussion_rounds: int = 3):
        self.llm_factory = llm_factory
        self.moderator = Moderator(llm_factory("moderator"))
        self.agents: Dict[str, Any] = {} # 暫存本次會議的專家實例
        self.max_discussion_rounds = max_discussion_rounds
        
        # 初始化 Dexter Planner
        try:
            planner_llm = llm_factory("planner")
            self.planner = DexterPlanner(llm_client=planner_llm)
            logger.info("✅ Dexter Planner 初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ Dexter Planner 初始化失敗，將使用 fallback: {e}")
            self.planner = None

    async def run_meeting(
        self, 
        symbol_key: str, 
        query: str, 
        event_callback: Optional[Callable[[MeetingEvent], None]] = None
    ) -> StructuredReport:
        """運行完整的會議流程（動態規劃支援）"""
        ctx = MeetingContext(symbol_key=symbol_key, query=query)
        ctx.metadata = {"state": MeetingState.INIT}
        
        # 建立 Scratchpad
        scratchpad = DexterScratchpad(query, symbol_key)
        ctx.metadata["scratchpad"] = scratchpad
        
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
        
        # 2. 初始 PLAN State
        ctx.metadata["state"] = MeetingState.PLAN
        await emit("status", {"message": "🤖 Dexter 正在規劃初始研究方案..."})
        
        plan = await self._create_and_execute_plan(
            query, 
            symbol_key, 
            scratchpad,
            trigger_reason="initial",
            emit=emit
        )
        
        # 3. 開場白
        ctx.metadata["state"] = MeetingState.DISCUSS
        await emit("status", {"message": "小韭菜進入會議室..."})
        opening = await self.moderator.generate_opening(ctx)
        ctx.history.append(opening)
        await emit("message", opening.dict())

        # 4. 多輪討論（支援動態數據請求）
        for round_num in range(1, self.max_discussion_rounds + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"討論 Round {round_num}")
            logger.info(f"{'='*60}")
            
            await emit("status", {"message": f"討論 Round {round_num}..."})
            
            # 專家發言
            round_messages = []
            for role_name in selected_roles:
                await emit("status", {"message": f"{role_name} 發表意見..."})
                agent_msg = await self._run_expert(role_name, ctx, emit)
                ctx.history.append(agent_msg)
                round_messages.append(agent_msg)
                await emit("message", agent_msg.dict())
            
            # 檢查是否有數據請求
            data_requests = self._extract_data_requests(round_messages)
            
            if not data_requests:
                logger.info("✅ 專家已滿意，結束討論")
                break
            
            # 處理數據請求
            logger.info(f"📊 偵測到 {len(data_requests)} 個數據請求")
            
            ctx.metadata["state"] = MeetingState.PLAN
            
            for request in data_requests:
                await emit("status", {
                    "message": f"🔄 處理 {request['requester']} 的數據請求..."
                })
                
                await self._create_and_execute_plan(
                    request["query"],
                    symbol_key,
                    scratchpad,
                    trigger_reason="expert_request",
                    requester=request["requester"],
                    emit=emit
                )
            
            ctx.metadata["state"] = MeetingState.DISCUSS

        # 5. 總結
        ctx.metadata["state"] = MeetingState.SYNTHESIZE
        await emit("status", {"message": "正在生成總結報告..."})
        report = await self.moderator.synthesize(ctx)
        
        # 儲存 scratchpad
        try:
            scratchpad.save_to_file()
        except Exception as e:
            logger.warning(f"Scratchpad 儲存失敗: {e}")
        
        ctx.metadata["state"] = MeetingState.FINISHED
        await emit("report", report.dict())
        await emit("finished", {"message": "會議結束"})
        
        return report

    async def _create_and_execute_plan(
        self,
        query: str,
        symbol_key: str,
        scratchpad: DexterScratchpad,
        trigger_reason: str,
        requester: Optional[str] = None,
        emit: Optional[Callable] = None
    ) -> Optional[ResearchPlan]:
        """
        生成並執行研究計畫
        
        Args:
            query: 查詢內容
            symbol_key: 股票代碼
            scratchpad: Scratchpad 實例
            trigger_reason: 觸發原因
            requester: 請求者
            emit: 事件發送函數
        """
        if not self.planner:
            logger.warning("Planner 不可用")
            return None
        
        try:
            # 生成計畫
            context = {
                "symbol_key": symbol_key,
                "scratchpad_summary": scratchpad.get_summary()
            }
            
            plan = await self.planner.create_plan(query, context=context)
            
            # 加入 scratchpad
            plan_id = scratchpad.add_plan(
                plan, 
                trigger_reason=trigger_reason,
                requester=requester
            )
            
            if emit:
                await emit("plan_generated", {
                    "plan_id": plan_id,
                    "objective": plan.objective,
                    "steps": len(plan.steps),
                    "constraints": plan.constraints,
                    "trigger_reason": trigger_reason,
                    "requester": requester
                })
            
            # 執行工具
            await self._execute_plan_tools(plan, plan_id, scratchpad, emit)
            
            scratchpad.mark_plan_executed(plan_id)
            
            return plan
            
        except Exception as e:
            logger.error(f"❌ 計畫生成/執行失敗: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _execute_plan_tools(
        self, 
        plan: ResearchPlan,
        plan_id: int,
        scratchpad: DexterScratchpad,
        emit: Optional[Callable] = None
    ):
        """執行計畫中的所有工具"""
        for i, step in enumerate(plan.steps, 1):
            try:
                if emit:
                    await emit("tool_start", {
                        "plan_id": plan_id,
                        "step_id": step.step_id,
                        "step": i,
                        "total": len(plan.steps),
                        "tool_name": step.tool_name
                    })
                
                logger.info(f"🔧 [{i}/{len(plan.steps)}] 執行工具: {step.tool_name}")
                
                # 從 dexter_tools 取得對應函數
                tool_func = getattr(dexter_tools, step.tool_name, None)
                
                if not tool_func:
                    logger.warning(f"⚠️ 工具 {step.tool_name} 不存在")
                    continue
                
                # 執行工具
                result = await tool_func(**step.args_schema)
                
                # 記錄到 scratchpad
                scratchpad.add_tool_result(step.step_id, result, plan_id)
                
                if emit:
                    await emit("tool_complete", {
                        "plan_id": plan_id,
                        "step_id": step.step_id,
                        "quality": result.quality,
                        "has_data": result.data is not None
                    })
                
                logger.info(f"   ✅ 完成，品質: {result.quality}")
                
            except Exception as e:
                logger.error(f"   ❌ 工具執行失敗: {e}")
                if emit:
                    await emit("tool_error", {
                        "plan_id": plan_id,
                        "step_id": step.step_id,
                        "error": str(e)
                    })

    def _extract_data_requests(self, messages: List[AgentMessage]) -> List[Dict[str, str]]:
        """從專家訊息中提取數據請求"""
        requests = []
        
        for msg in messages:
            # 尋找 <data_request>...</data_request> 標記
            pattern = r'<data_request>(.*?)</data_request>'
            matches = re.findall(pattern, msg.content, re.DOTALL)
            
            for match in matches:
                request_query = match.strip()
                requests.append({
                    "requester": msg.agent_name,
                    "query": request_query
                })
                logger.info(f"   📝 發現請求: {msg.agent_name} → {request_query[:50]}...")
        
        return requests

    async def _run_expert(self, role: str, ctx: MeetingContext, emit_f: Callable) -> AgentMessage:
        """執行單個專家（使用 scratchpad context）"""
        llm = self.llm_factory(role)
        
        scratchpad = ctx.metadata.get("scratchpad")
        
        # 建立專家 System Prompt
        history_summary = "\n".join([f"[{m.agent_name}]: {m.content}" for m in ctx.history])
        
        # 加入 scratchpad 上下文
        scratchpad_context = ""
        if scratchpad:
            scratchpad_context = f"\n\n## 已收集的研究數據\n\n{scratchpad.format_for_llm()}"
        
        system_prompt = f"""
        你是一位專業的股票分析師，角色為: {role}。
        你正在參加一場關於 {ctx.symbol_key} 的研討會。
        目前討論的主題是: {ctx.query}
        
        之前的討論記錄如下:
        {history_summary}
        
        {scratchpad_context}
        
        請在遵守你的專業立場下，提出你的見解。
        
        如果你需要額外的數據來驗證假設或觀點，請使用以下格式請求:
        <data_request>你需要的數據描述，例如：AAPL 過去三個月成交量</data_request>
        
        你可以使用以下工具來獲取最新數據:
        {tool_registry.get_tool_schemas()}
        
        你需要先思考 (Thinking)，然後決定是否需要額外數據，最後給出結論。
        """
        
        response = await llm.ainvoke(system_prompt)
        content = response.content
        
        return AgentMessage(
            agent_id=role,
            agent_name=f"{role.capitalize()} Analyst",
            role=MessageRole(role),
            content=content,
            msg_type=MsgType.OPINION
        )
