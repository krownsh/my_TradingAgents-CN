#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dexter Scratchpad - 上下文管理

儲存研究計畫執行歷史，管理工具呼叫記錄，提供 LLM 上下文
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .schemas import ResearchPlan, DexterToolOutput
from .repository import ResearchRepository
from tradingagents.models.research import ResearchEvent, ResearchSessionSummary

logger = logging.getLogger(__name__)


class DexterScratchpad:
    """
    Dexter Scratchpad - 管理研究過程的所有數據與計畫
    
    功能：
    1. 儲存多個研究計畫（支援動態追加）
    2. 記錄所有工具執行結果
    3. 提供格式化的 LLM 上下文
    4. 上下文管理（超過限制時清理舊資料）
    """
    
    def __init__(self, query: str, symbol_key: str, session_id: Optional[str] = None):
        self.query = query
        self.symbol_key = symbol_key
        self.session_id = session_id or f"rex_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.created_at = datetime.now()
        
        # 初始化持久化 Repository
        self.repository = ResearchRepository()
        
        # 儲存所有計畫（按執行順序）
        self.plans: List[Dict[str, Any]] = []
        
        # 儲存所有工具結果 {step_id: result}
        self.tool_results: Dict[str, DexterToolOutput] = {}
        
        # 計畫計數器
        self.plan_counter = 0
        
        # 初始同步會話摘要
        self._sync_session_summary()
        
    def add_plan(
        self, 
        plan: ResearchPlan, 
        trigger_reason: str = "initial",
        requester: Optional[str] = None
    ) -> int:
        """
        新增研究計畫
        
        Args:
            plan: 研究計畫物件
            trigger_reason: 觸發原因（'initial', 'expert_request', 'iteration'）
            requester: 請求者（專家名稱，若為 expert_request）
            
        Returns:
            plan_id: 計畫 ID
        """
        self.plan_counter += 1
        plan_id = self.plan_counter
        
        plan_record = {
            "plan_id": plan_id,
            "objective": plan.objective,
            "constraints": plan.constraints,
            "steps": [step.dict() for step in plan.steps],
            "symbol_key": plan.symbol_key,
            "trigger_reason": trigger_reason,
            "requester": requester,
            "created_at": datetime.now().isoformat(),
            "executed": False
        }
        
        self.plans.append(plan_record)
        logger.info(f"📋 新增計畫 #{plan_id}: {plan.objective} (觸發: {trigger_reason})")
        
        # 同步至資料庫
        self._sync_session_summary()
        
        return plan_id
    
    def mark_plan_executed(self, plan_id: int):
        """標記計畫已執行"""
        for plan in self.plans:
            if plan["plan_id"] == plan_id:
                plan["executed"] = True
                break
    
    def add_tool_result(
        self, 
        step_id: str, 
        result: DexterToolOutput,
        plan_id: Optional[int] = None
    ):
        """
        新增工具執行結果
        
        Args:
            step_id: 步驟 ID
            result: 工具輸出
            plan_id: 所屬計畫 ID（可選）
        """
        self.tool_results[step_id] = result
        
        # 如果指定了 plan_id，更新計畫中的步驟狀態
        if plan_id:
            for plan in self.plans:
                if plan["plan_id"] == plan_id:
                    for step in plan["steps"]:
                        if step["step_id"] == step_id:
                            step["executed"] = True
                            step["quality"] = result.quality
                            break
                    break
        
        logger.debug(f"   ✅ 記錄工具結果: {step_id}, 品質: {result.quality}")
        
        # 持久化事件
        self._persist_event(step_id, result, plan_id)
        # 更新摘要
        self._sync_session_summary()
    
    def _persist_event(self, step_id: str, result: DexterToolOutput, plan_id: Optional[int]):
        """將工具執行結果作為研究事件持久化"""
        try:
            # 尋找對應的參數 (從計畫中找)
            args = {}
            if plan_id:
                for plan in self.plans:
                    if plan["plan_id"] == plan_id:
                        for step in plan["steps"]:
                            if step["step_id"] == step_id:
                                args = step.get("args_schema", {})
                                break
            
            event = ResearchEvent(
                event_id=step_id,
                plan_id=plan_id or 0,
                symbol_key=self.symbol_key,
                tool_name=result.source_provider,
                args=args,
                data=result.data,
                quality=result.quality,
                source_provider=result.source_provider,
                message=result.message,
                timestamp=datetime.now(),
                trigger_reason="execution"
            )
            self.repository.save_event(event)
        except Exception as e:
            logger.error(f"❌ 持久化 ResearchEvent 失敗: {e}")

    def _sync_session_summary(self):
        """同步會話狀態至資料庫"""
        try:
            summary = ResearchSessionSummary(
                session_id=self.session_id,
                symbol_key=self.symbol_key,
                query=self.query,
                plans=self.plans,
                total_tools_called=len(self.tool_results),
                updated_at=datetime.now()
            )
            self.repository.save_session_summary(summary)
        except Exception as e:
            logger.error(f"❌ 同步會話摘要失敗: {e}")
    
    def get_all_tool_results(self) -> Dict[str, DexterToolOutput]:
        """取得所有工具結果"""
        return self.tool_results
    
    def get_plan_data(self, plan_id: Optional[int] = None) -> Dict[str, Any]:
        """
        取得計畫的工具執行資料
        
        Args:
            plan_id: 計畫 ID，若為 None 則回傳最新計畫
            
        Returns:
            {step_id: {data, quality, provider, message}}
        """
        if plan_id is None:
            plan_id = self.plan_counter
        
        # 找到計畫
        target_plan = None
        for plan in self.plans:
            if plan["plan_id"] == plan_id:
                target_plan = plan
                break
        
        if not target_plan:
            return {}
        
        # 取得該計畫的所有步驟結果
        plan_data = {}
        for step in target_plan["steps"]:
            step_id = step["step_id"]
            if step_id in self.tool_results:
                result = self.tool_results[step_id]
                plan_data[step_id] = {
                    "data": result.data,
                    "quality": result.quality,
                    "provider": result.source_provider,
                    "message": result.message
                }
        
        return plan_data
    
    def format_for_llm(self, max_plans: int = 3) -> str:
        """
        格式化為 LLM 可讀的上下文
        
        Args:
            max_plans: 最多包含幾個計畫（從最新往前）
            
        Returns:
            格式化的文字
        """
        if not self.plans:
            return "尚無研究計畫。"
        
        # 取最新的 N 個計畫
        recent_plans = self.plans[-max_plans:]
        
        context_lines = [
            f"## 研究查詢: {self.query}",
            f"## 股票代碼: {self.symbol_key}",
            f"## 計畫數量: {len(self.plans)}",
            ""
        ]
        
        for plan in recent_plans:
            plan_id = plan["plan_id"]
            context_lines.append(f"### 計畫 #{plan_id}: {plan['objective']}")
            context_lines.append(f"觸發: {plan['trigger_reason']}")
            
            if plan.get('requester'):
                context_lines.append(f"請求者: {plan['requester']}")
            
            context_lines.append(f"\n執行步驟:")
            
            for step in plan["steps"]:
                step_id = step["step_id"]
                tool_name = step["tool_name"]
                
                if step_id in self.tool_results:
                    result = self.tool_results[step_id]
                    context_lines.append(
                        f"  ✅ {tool_name} - 品質: {result.quality}, "
                        f"來源: {result.source_provider}"
                    )
                    
                    # 簡要資料摘要
                    if result.data:
                        data_summary = self._summarize_data(result.data)
                        context_lines.append(f"     摘要: {data_summary}")
                else:
                    context_lines.append(f"  ⏳ {tool_name} - 尚未執行")
            
            context_lines.append("")
        
        return "\n".join(context_lines)
    
    def _summarize_data(self, data: Any, max_length: int = 100) -> str:
        """簡要資料摘要"""
        if isinstance(data, list):
            return f"{len(data)} 筆資料"
        elif isinstance(data, dict):
            keys = list(data.keys())[:3]
            return f"包含欄位: {', '.join(keys)}..."
        elif isinstance(data, str):
            return data[:max_length] + "..." if len(data) > max_length else data
        else:
            return str(data)[:max_length]
    
    def get_summary(self) -> Dict[str, Any]:
        """取得 Scratchpad 摘要"""
        return {
            "query": self.query,
            "symbol_key": self.symbol_key,
            "total_plans": len(self.plans),
            "total_tool_calls": len(self.tool_results),
            "created_at": self.created_at.isoformat(),
            "latest_plan": self.plans[-1] if self.plans else None
        }
    
    def save_to_file(self, filepath: Optional[Path] = None):
        """
        儲存到 JSON 檔案
        
        Args:
            filepath: 檔案路徑，若為 None 則自動生成
        """
        if filepath is None:
            # 自動生成檔案名稱
            timestamp = self.created_at.strftime("%Y%m%d_%H%M%S")
            symbol = self.symbol_key.replace(":", "_")
            filepath = Path(f".dexter/scratchpad/{timestamp}_{symbol}.json")
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 準備資料（將 DexterToolOutput 轉為 dict）
        tool_results_dict = {
            step_id: result.dict() 
            for step_id, result in self.tool_results.items()
        }
        
        data = {
            "query": self.query,
            "symbol_key": self.symbol_key,
            "created_at": self.created_at.isoformat(),
            "plans": self.plans,
            "tool_results": tool_results_dict
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Scratchpad 已儲存: {filepath}")
