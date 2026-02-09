"""
Dexter Planner 測試腳本

測試研究計畫生成功能
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.dexter_adapter.planner import DexterPlanner
from tradingagents.graph.trading_graph import create_llm_by_provider
from tradingagents.utils.async_utils import run_async
from app.services.config_service import config_service


async def test_planner():
    """測試 Dexter Planner"""
    print("\n" + "="*60)
    print("測試: Dexter Planner")
    print("="*60)
    
    # 從配置獲取 LLM
    try:
        config = await config_service.get_system_config()
        if not config:
            print("⚠️ 無法讀取系統配置，將使用預設 OpenAI")
            llm = None
        else:
            settings = config.system_settings
            model_name = settings.get("deep_analysis_model") or config.default_llm
            llm_cfg = next((c for c in config.llm_configs if c.model_name == model_name), config.llm_configs[0])
            
            print(f"📊 使用 LLM: {llm_cfg.provider.value} / {llm_cfg.model_name}")
            
            llm = create_llm_by_provider(
                provider=llm_cfg.provider.value,
                model=llm_cfg.model_name,
                backend_url=llm_cfg.api_base,
                temperature=0.3,
                max_tokens=llm_cfg.max_tokens,
                timeout=llm_cfg.timeout or 60,
                api_key=llm_cfg.api_key
            )
    except Exception as e:
        print(f"⚠️ LLM 初始化失敗: {e}")
        llm = None
    
    # 建立 planner
    planner = DexterPlanner(llm_client=llm)
    
    # 測試查詢列表
    test_queries = [
        "AAPL 過去一年表現如何？",
        "台積電近期有哪些重要消息？",
        "比較 AAPL 和 TSLA 的營收成長",
        "US:MSFT 的財務狀況如何？"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"📝 問題: {query}")
        print(f"{'='*60}")
        
        try:
            plan = await planner.create_plan(query)
            
            print(f"\n✅ 計畫生成成功:")
            print(f"  目標: {plan.objective}")
            print(f"  限制: {plan.constraints}")
            print(f"  符號: {plan.symbol_key or 'N/A'}")
            print(f"\n  執行步驟 ({len(plan.steps)} 步):")
            
            for i, step in enumerate(plan.steps, 1):
                print(f"\n  {i}. [{step.step_id}] {step.tool_name}")
                print(f"     參數: {step.args_schema}")
                print(f"     預期: {step.expected_output}")
                if step.validation_rules:
                    print(f"     驗證: {', '.join(step.validation_rules)}")
            
        except Exception as e:
            print(f"\n❌ 計畫生成失敗: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("✅ 測試完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(test_planner())
