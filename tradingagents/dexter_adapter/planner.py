"""
Dexter Planner - 研究計畫生成器

Python 版本的 Dexter planning 邏輯，使用 LLM 生成結構化的研究計畫。
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
import json

from tradingagents.dexter_adapter.schemas import ResearchPlan, ResearchStep
from tradingagents.dexter_adapter.tools import (
    dexter_get_price_snapshot,
    dexter_get_prices,
    dexter_get_news,
    dexter_get_income_statement,
    dexter_get_balance_sheet,
    dexter_get_cash_flow
)

logger = logging.getLogger(__name__)


# 可用工具定義（用於 system prompt）
AVAILABLE_TOOLS = {
    "dexter_get_price_snapshot": {
        "description": "獲取股票即時報價（最新價格、漲跌幅、成交量等）",
        "params": {"symbol_key": "US:AAPL or TW:2330"},
        "example": "查詢 AAPL 當前股價"
    },
    "dexter_get_prices": {
        "description": "獲取歷史價格數據（K線資料）",
        "params": {
            "symbol_key": "US:AAPL or TW:2330",
            "start_date": "YYYY-MM-DD (optional)",
            "end_date": "YYYY-MM-DD (optional)"
        },
        "example": "查詢 AAPL 過去 30 天股價走勢"
    },
    "dexter_get_news": {
        "description": "獲取新聞與公告（US: 新聞, TW: MOPS 公告）",
        "params": {
            "symbol_key": "US:AAPL or TW:2330",
            "limit": "int (default 10)"
        },
        "example": "查詢台積電最近公告"
    },
    "dexter_get_income_statement": {
        "description": "獲取損益表（僅 US 市場）",
        "params": {
            "symbol_key": "US:AAPL",
            "period": "annual or quarterly",
            "limit": "int (default 5)"
        },
        "market_support": "US only, TW returns MISSING"
    },
    "dexter_get_balance_sheet": {
        "description": "獲取資產負債表（僅 US 市場）",
        "params": {"symbol_key": "US:AAPL", "period": "annual/quarterly"},
        "market_support": "US only"
    },
    "dexter_get_cash_flow": {
        "description": "獲取現金流量表（僅 US 市場）",
        "params": {"symbol_key": "US:AAPL", "period": "annual/quarterly"},
        "market_support": "US only"
    }
}


def build_planning_system_prompt() -> str:
    """建立 Planner 的 system prompt"""
    current_date = datetime.now().strftime("%Y年%m月%d日 %A")
    
    tool_list = "\n".join([
        f"- **{name}**: {info['description']}\n  參數: {info['params']}"
        for name, info in AVAILABLE_TOOLS.items()
    ])
    
    return f"""你是 Dexter Research Planner，負責將使用者的研究問題分解為結構化的執行計畫。

當前日期: {current_date}

## 可用工具

{tool_list}

## 規劃原則

1. **Symbol Key 規範**
   - 必須使用完整格式：`US:AAPL` 或 `TW:2330`
   - 公司名稱需轉換為代碼（Apple → US:AAPL, 台積電 → TW:2330）

2. **工具選擇策略**
   - 價格相關：用 `dexter_get_prices`（歷史）或 `dexter_get_price_snapshot`（當前）
   - 新聞公告：用 `dexter_get_news`
   - 財報分析：用 `dexter_get_income_statement` 等（僅 US）

3. **市場差異處理**
   - US 市場：所有工具可用
   - TW 市場：僅價格與新聞/公告，財報回傳 MISSING

4. **日期處理**
   - "過去一年" → start_date 為一年前，end_date 為今日
   - "近期" → 近 30 天
   - "YTD" → start_date 為今年 1/1

5. **驗證規則**
   - price_range_valid: 價格範圍合理
   - date_alignment: 日期範圍正確
   - data_completeness: 資料完整性

## 輸出格式

你必須輸出 JSON 格式的研究計畫：

{{
  "objective": "研究目標描述",
  "constraints": {{
    "market": "US 或 TW",
    "date_range": ["start_date", "end_date"],
    "quality": "EOD 或 REALTIME"
  }},
  "steps": [
    {{
      "step_id": "step_1",
      "tool_name": "dexter_get_prices",
      "args_schema": {{
        "symbol_key": "US:AAPL",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
      }},
      "expected_output": "AAPL 2024 全年每日價格資料",
      "validation_rules": ["price_range_valid", "date_alignment"]
    }}
  ]
}}

## 範例

**問題**: "AAPL 過去一年表現如何？"

**計畫**:
{{
  "objective": "分析 AAPL 過去一年股價表現與相關新聞",
  "constraints": {{"market": "US", "date_range": ["2023-02-09", "2024-02-09"]}},
  "steps": [
    {{
      "step_id": "step_1",
      "tool_name": "dexter_get_prices",
      "args_schema": {{"symbol_key": "US:AAPL", "start_date": "2023-02-09", "end_date": "2024-02-09"}},
      "expected_output": "AAPL 一年內每日價格",
      "validation_rules": ["price_range_valid", "date_alignment"]
    }},
    {{
      "step_id": "step_2",
      "tool_name": "dexter_get_news",
      "args_schema": {{"symbol_key": "US:AAPL", "limit": 10}},
      "expected_output": "AAPL 相關重要新聞",
      "validation_rules": ["data_completeness"]
    }}
  ]
}}
"""


class DexterPlanner:
    """Dexter 研究計畫生成器"""
    
    def __init__(self, llm_client=None):
        """
        初始化 Planner
        
        Args:
            llm_client: LangChain ChatModel (如 ChatOpenAI)，若未提供則使用預設
        """
        if llm_client is None:
            # 使用預設  LangChain OpenAI
            from langchain_openai import ChatOpenAI
            import os
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("請設置 OPENAI_API_KEY 環境變數或提供 llm_client")
                
            self.llm_client = ChatOpenAI(
                model="gpt-4",
                temperature=0.3,
                api_key=api_key
            )
        else:
            self.llm_client = llm_client
            
        self.system_prompt = build_planning_system_prompt()
        
    async def create_plan(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ResearchPlan:
        """
        生成研究計畫
        
        Args:
            query: 使用者的研究問題
            context: 額外上下文（如指定市場、時間範圍等）
            
        Returns:
            ResearchPlan: 結構化的研究計畫
            
        Example:
            >>> planner = DexterPlanner()
            >>> plan = await planner.create_plan("台積電近期有哪些重要消息？")
            >>> print(plan.steps[0].tool_name)
            dexter_get_news
        """
        # 建立 user prompt
        user_prompt = f"請為以下研究問題生成執行計畫：\n\n{query}"
        
        if context:
            user_prompt += f"\n\n額外條件：{json.dumps(context, ensure_ascii=False, indent=2)}"
        
        user_prompt += "\n\n請輸出 JSON 格式的研究計畫。"
        
        try:
            # 呼叫 LLM (使用 LangChain 標準 invoke)
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # 如果 llm_client 有 ainvoke 使用 ainvoke，否則用 invoke
            if hasattr(self.llm_client, 'ainvoke'):
                response = await self.llm_client.ainvoke(messages)
            else:
                response = self.llm_client.invoke(messages)
            
            # 解析 response
            content = response.content
            plan_dict = json.loads(content)
            
            # 轉換為 ResearchPlan
            steps = [
                ResearchStep(
                    step_id=step["step_id"],
                    tool_name=step["tool_name"],
                    args_schema=step["args_schema"],
                    expected_output=step["expected_output"],
                    validation_rules=step.get("validation_rules", [])
                )
                for step in plan_dict.get("steps", [])
            ]
            
            # 推測 symbol_key（從第一個步驟提取）
            symbol_key = None
            if steps and "symbol_key" in steps[0].args_schema:
                symbol_key = steps[0].args_schema["symbol_key"]
            
            return ResearchPlan(
                objective=plan_dict.get("objective", query),
                constraints=plan_dict.get("constraints", {}),
                steps=steps,
                symbol_key=symbol_key
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response content: {content if 'content' in locals() else 'N/A'}")
            # Fallback: 建立簡單的單步驟計畫
            return self._create_fallback_plan(query)
        except Exception as e:
            logger.error(f"Error creating plan: {e}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(query)
    
    def _create_fallback_plan(self, query: str) -> ResearchPlan:
        """建立 fallback 計畫（LLM 失敗時使用）"""
        return ResearchPlan(
            objective=f"回答問題：{query}",
            constraints={"quality": "UNKNOWN"},
            steps=[
                ResearchStep(
                    step_id="fallback_1",
                    tool_name="dexter_get_news",
                    args_schema={"symbol_key": "US:AAPL", "limit": 5},
                    expected_output="相關資訊",
                    validation_rules=[]
                )
            ]
        )
