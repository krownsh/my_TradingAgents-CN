import asyncio
import os
import sys
from datetime import datetime

# 加入項目根目錄
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.append(current_dir)

from tradingagents.dexter_adapter.validator import DexterValidator
from tradingagents.dexter_adapter.scratchpad import DexterScratchpad
from tradingagents.dexter_adapter.schemas import ResearchPlan, ResearchStep
from tradingagents.dexter_adapter.repository import ResearchRepository

async def test_validator():
    print("--- 測試驗證器 (DexterValidator) ---")
    validator = DexterValidator(max_tools_per_plan=2)
    scratchpad = DexterScratchpad(query="測試執行", symbol_key="TW:2330")
    
    # 1. 測試超量步驟檢查
    plan_long = ResearchPlan(
        objective="太長的計畫",
        symbol_key="TW:2330",
        steps=[
            ResearchStep(step_id="s1", tool_name="tool", args_schema={}, expected_output="o1"),
            ResearchStep(step_id="s2", tool_name="tool", args_schema={}, expected_output="o2"),
            ResearchStep(step_id="s3", tool_name="tool", args_schema={}, expected_output="o3")
        ]
    )
    ok, reason = await validator.validate_plan(plan_long, scratchpad)
    print(f"[測試 1] 超量檢查 (預期失敗): {ok}, 原因: {reason}")
    
    # 2. 測試市場不匹配
    plan_mismatch = ResearchPlan(
        objective="市場不匹配",
        symbol_key="TW:2330",
        steps=[
            ResearchStep(step_id="s1", tool_name="tool", args_schema={"symbol": "US:AAPL"}, expected_output="o1")
        ]
    )
    ok, reason = await validator.validate_plan(plan_mismatch, scratchpad)
    print(f"[測試 2] 市場檢查 (預期失敗): {ok}, 原因: {reason}")
    
    # 3. 測試正常計畫
    plan_ok = ResearchPlan(
        objective="正常的計畫",
        symbol_key="TW:2330",
        steps=[
            ResearchStep(step_id="s1", tool_name="tool", args_schema={"symbol": "TW:2330"}, expected_output="o1")
        ]
    )
    ok, reason = await validator.validate_plan(plan_ok, scratchpad)
    print(f"[測試 3] 正常檢查 (預期成功): {ok}, 原因: {reason}")

async def test_persistence():
    print("\n--- 測試持久化 (MongoDB Persistence) ---")
    repo = ResearchRepository()
    if not repo._connected:
        print("❌ MongoDB 未連接，無法測試持久化。")
        return
        
    session_id = f"test_res_{datetime.now().strftime('%H%M%S')}"
    scratchpad = DexterScratchpad(query="自動同步測試", symbol_key="TW:2330", session_id=session_id)
    
    # 模擬工具執行
    from tradingagents.dexter_adapter.schemas import DexterToolOutput
    output = DexterToolOutput(
        data={"price": 100},
        quality="REALTIME",
        source_provider="test_provider",
        asof=datetime.now(),
        message="success"
    )
    scratchpad.add_tool_result("test_step_1", output)
    
    # 檢查存儲
    event = repo.db["research_events"].find_one({"event_id": "test_step_1"})
    print(f"ResearchEvent 存儲狀態: {'✅' if event else '❌'}")
    
    session = repo.db["research_sessions"].find_one({"session_id": session_id})
    print(f"Session Summary 存儲狀態: {'✅' if session else '❌'}")

if __name__ == "__main__":
    asyncio.run(test_validator())
    asyncio.run(test_persistence())
