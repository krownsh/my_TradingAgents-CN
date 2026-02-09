"""
測試 PLAN State 整合

測試會議室整合 Dexter Planner 後的完整流程
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tradingagents.meeting.orchestrator import MeetingOrchestrator
from tradingagents.graph.trading_graph import create_llm_by_provider
from tradingagents.utils.async_utils import run_async
from app.services.config_service import config_service


def print_event(event):
    """打印會議事件"""
    event_type = event.get("event_type", "unknown")
    payload = event.get("payload", {})
    
    if event_type == "status":
        print(f"\n📢 {payload.get('message')}")
    elif event_type == "plan_generated":
        print(f"\n✅ 計畫生成:")
        print(f"   目標: {payload.get('objective')}")
        print(f"   步驟數: {payload.get('steps')}")
    elif event_type == "tool_start":
        step = payload.get('step')
        total = payload.get('total')
        tool_name = payload.get('tool_name')
        print(f"\n🔧 [{step}/{total}] 執行工具: {tool_name}")
    elif event_type == "tool_complete":
        quality = payload.get('quality')
        has_data = payload.get('has_data')
        print(f"   ✅ 完成，品質: {quality}, 有資料: {has_data}")
    elif event_type == "tool_error":
        error = payload.get('error')
        print(f"   ❌ 錯誤: {error}")
    elif event_type == "message":
        agent_name = payload.get('agent_name', 'Unknown')
        content = payload.get('content', '')[:200]  # 截斷過長內容
        print(f"\n💬 [{agent_name}]: {content}...")
    elif event_type == "report":
        print(f"\n📊 最終報告已生成")
    elif event_type == "finished":
        print(f"\n✅ {payload.get('message')}")


async def test_meeting_with_plan():
    """測試會議室 PLAN state"""
    print("\n" + "="*60)
    print("測試: 會議室 PLAN State 整合")
    print("="*60)
    
    # 從配置獲取 LLM
    try:
        config = await config_service.get_system_config()
        if not config:
            print("⚠️ 無法讀取系統配置")
            return
        
        settings = config.system_settings
        model_name = settings.get("deep_analysis_model") or config.default_llm
        llm_cfg = next((c for c in config.llm_configs if c.model_name == model_name), config.llm_configs[0])
        
        print(f"📊 使用 LLM: {llm_cfg.provider.value} / {llm_cfg.model_name}")
        
        # LLM factory
        def llm_factory(role):
            return create_llm_by_provider(
                provider=llm_cfg.provider.value,
                model=llm_cfg.model_name,
                backend_url=llm_cfg.api_base,
                temperature=0.3 if role == "planner" else 0.1,
                max_tokens=llm_cfg.max_tokens,
                timeout=llm_cfg.timeout or 120,
                api_key=llm_cfg.api_key
            )
        
        # 建立 orchestrator
        orchestrator = MeetingOrchestrator(llm_factory)
        
        # 測試查詢
        test_cases = [
            ("US:AAPL", "AAPL 過去一個月股價表現如何？"),
            ("TW:2330", "台積電最近有哪些重要公告？"),
        ]
        
        for symbol_key, query in test_cases:
            print(f"\n{'='*60}")
            print(f"🔍 測試: {query}")
            print(f"   符號: {symbol_key}")
            print(f"{'='*60}")
            
            try:
                report = await orchestrator.run_meeting(
                    symbol_key=symbol_key,
                    query=query,
                    event_callback=print_event
                )
                
                print(f"\n\n📋 會議報告:")
                print(f"   標題: {report.title}")
                print(f"   執行摘要: {report.executive_summary[:200]}...")
                
            except Exception as e:
                print(f"\n❌ 測試失敗: {e}")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        print(f"⚠️ 初始化失敗: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("✅ 測試完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(test_meeting_with_plan())
