#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dexter Validator - 研究計畫驗證器
負責檢查計畫安全性、效率與市場正確性
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from .schemas import ResearchPlan
from .scratchpad import DexterScratchpad

logger = logging.getLogger(__name__)

class DexterValidator:
    """
    研究計畫驗證層
    
    職責：
    1. 安全性：防止工具瘋狂調用 (Rate Limiting / Count Limiting)
    2. 效率：偵測重複的數據請求，減少 Token 浪費
    3. 正確性：檢查工具參數與市場 (Global/TW/US) 是否適配
    """
    
    def __init__(self, max_tools_per_plan: int = 15):
        self.max_tools_per_plan = max_tools_per_plan

    async def validate_plan(self, plan: ResearchPlan, scratchpad: DexterScratchpad) -> Tuple[bool, str]:
        """
        執行多維度驗證
        
        Args:
            plan: 待驗證的研究計畫
            scratchpad: 目前的研究上下文紀錄
            
        Returns:
            (is_valid, reason)
        """
        if not plan.steps:
            return False, "研究計畫不包含任何步驟。"

        # 1. 檢查工具數量上限
        if len(plan.steps) > self.max_tools_per_plan:
            return False, f"計畫步驟過多 ({len(plan.steps)} > {self.max_tools_per_plan})，已觸發安全熔斷。請拆分任務。"

        # 2. 市場正確性校核 (Market-Aware Validation)
        market_ok, market_error = self._check_market_compatibility(plan)
        if not market_ok:
            return False, f"市場邏輯錯誤: {market_error}"

        # 3. 冗餘偵測 (Efficiency / Redundancy Check)
        redundant_steps = self._find_redundant_steps(plan, scratchpad)
        if redundant_steps:
            logger.info(f"💡 偵測到 {len(redundant_steps)} 個冗餘步驟，建議跳過以節省 API 額度。")
            # 在目前的流程中，我們不因為冗餘而終止計畫，但我們會標記它們
            for step in plan.steps:
                if step.step_id in redundant_steps:
                    step.metadata = step.metadata or {}
                    step.metadata["is_redundant"] = True
                    step.metadata["redundancy_reason"] = "之前已獲取相同或相似數據"

        return True, "驗證通過"

    def _check_market_compatibility(self, plan: ResearchPlan) -> Tuple[bool, str]:
        """
        檢查計畫中的工具是否適用於當前市場
        """
        symbol_key = plan.symbol_key
        market = ""
        if ":" in symbol_key:
            market = symbol_key.split(":")[0].upper()
        
        for step in plan.steps:
            tool_name = step.tool_name
            args = step.args_schema or {}
            
            # 範例規則：
            # 如果是台股 (TW)，卻調用了僅限美股的工具（假設有）
            # 或者 symbol_key 與工具參數中的 symbol 不一致
            if "symbol" in args and args["symbol"] != symbol_key:
                return False, f"工具 {tool_name} 的參數 symbol ({args['symbol']}) 與計畫 symbol ({symbol_key}) 不一致。"
                
            # 特殊市場工具限制
            if market == "TW":
                 # 假設未來有僅限美股的工具名為 us_xxx
                 if tool_name.startswith("us_"):
                     return False, f"台股市場不支援執行美股專屬工具 {tool_name}。"
            
        return True, ""

    def _find_redundant_steps(self, plan: ResearchPlan, scratchpad: DexterScratchpad) -> List[str]:
        """
        尋找計畫中與過去執行結果重複的步驟
        """
        redundant_step_ids = []
        history = scratchpad.get_all_tool_results()
        
        for step in plan.steps:
            step_id = step.step_id
            tool_name = step.tool_name
            args = step.args_schema or {}
            
            # 1. 直接 ID 匹配
            if step_id in history:
                redundant_step_ids.append(step_id)
                continue
                
            # 2. 參數特徵匹配 (更深層次)
            for hist_id, hist_result in history.items():
                if hist_result.source_provider == tool_name:
                    # 如果工具相同且輸入參數高度相似（這裡簡化處理）
                    # 實際上可以透過 Hash 或 LLM 比較
                    pass
                    
        return redundant_step_ids
