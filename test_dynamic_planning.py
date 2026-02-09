#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試動態規劃功能

測試多輪 PLAN-DISCUSS 循環與專家數據請求
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.meeting.orchestrator import MeetingOrchestrator
from tradingagents.llm import get_llm


async def test_dynamic_planning():
    """測試動態規劃：專家請求額外數據"""
    
    print("\n" + "="*60)
    print("測試動態規劃功能")
    print("="*60 + "\n")
    
    # 建立 orchestrator（最多 2 輪討論）
    orchestrator = MeetingOrchestrator(
        llm_factory=lambda role: get_llm("gpt-4o-mini"),
        max_discussion_rounds=2
    )
    
    # 測試場景：初始查詢可能觸發專家請求更多數據
    query = "AAPL 最近是漲還是跌？"
    symbol_key = "US:AAPL"
    
    events = []
    
    def event_handler(event):
        """記錄所有事件"""
        events.append(event)
        print(f"[EVENT] {event.event_type}: {event.payload.get('message', '')}")
        
        if event.event_type == "plan_generated":
            plan_id = event.payload.get("plan_id")
            objective = event.payload.get("objective")
            trigger = event.payload.get("trigger_reason")
            requester = event.payload.get("requester")
            
            print(f"\n📋 計畫 #{plan_id} 生成")
            print(f"   目標: {objective}")
            print(f"   觸發: {trigger}")
            if requester:
                print(f"   請求者: {requester}")
    
    try:
        report = await orchestrator.run_meeting(
            symbol_key=symbol_key,
            query=query,
            event_callback=event_handler
        )
        
        print("\n" + "="*60)
        print("📊 會議報告")
        print("="*60)
        print(f"\n{report.content}\n")
        
        # 分析事件
        plan_events = [e for e in events if e.event_type == "plan_generated"]
        print(f"\n✅ 共生成 {len(plan_events)} 個研究計畫")
        
        for event in plan_events:
            payload = event.payload
            print(f"   計畫 #{payload['plan_id']}: {payload['trigger_reason']}")
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


async def test_expert_data_request():
    """
    測試專家明確請求數據（需要手動模擬）
    
    實際測試中，專家需要在輸出中包含：
    <data_request>我需要 AAPL 過去三個月成交量</data_request>
    """
    print("\n" + "="*60)
    print("測試專家數據請求（模擬）")
    print("="*60 + "\n")
    
    print("注意：實際測試需要 LLM 在專家回覆中包含 <data_request> 標記")
    print("可以透過 System Prompt 引導專家使用此標記")


if __name__ == "__main__":
    print("""
    動態規劃測試腳本
    
    測試功能：
    1. Scratchpad 多計畫儲存
    2. 多輪 PLAN-DISCUSS 循環
    3. 專家 <data_request> 解析
    4. 動態計畫生成
    
    """)
    
    asyncio.run(test_dynamic_planning())
    asyncio.run(test_expert_data_request())
