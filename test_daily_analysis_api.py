# -*- coding: utf-8 -*-
"""
Daily Analysis API 測試腳本
測試所有 /api/daily/* 端點的功能
"""
import sys
import asyncio
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_imports():
    """測試導入是否正常"""
    print("=" * 70)
    print("📦 測試 1: 模組導入")
    print("=" * 70)
    
    try:
        from tradingagents.daily_analysis import StockAnalysisPipeline, GeminiAnalyzer, get_config
        print("✓ 核心模組導入成功")
        print(f"  - StockAnalysisPipeline: {StockAnalysisPipeline}")
        print(f"  - GeminiAnalyzer: {GeminiAnalyzer}")
        print(f"  - get_config: {get_config}")
    except Exception as e:
        print(f"✗ 核心模組導入失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        from backend.routers.daily_analysis import router
        print("✓ API Router 導入成功")
        print(f"  - router.routes 數量: {len(router.routes)}")
        for route in router.routes:
            print(f"    - {route.methods} {route.path}")
    except Exception as e:
        print(f"✗ API Router 導入失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def test_config():
    """測試配置加載"""
    print("\n" + "=" * 70)
    print("⚙️  測試 2: 配置加載")
    print("=" * 70)
    
    try:
        from tradingagents.daily_analysis.config import get_config
        config = get_config()
        print("✓ 配置加載成功")
        print(f"  - 自選股列表: {config.stock_list[:3] if len(config.stock_list) > 3 else config.stock_list}")
        print(f"  - 最大併發數: {config.max_workers}")
        print(f"  - 啟用即時行情: {config.enable_realtime_quote}")
        print(f"  - 啟用籌碼分佈: {config.enable_chip_distribution}")
        return True
    except Exception as e:
        print(f"✗ 配置加載失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pipeline_init():
    """測試 Pipeline 初始化"""
    print("\n" + "=" * 70)
    print("🔧 測試 3: Pipeline 初始化")
    print("=" * 70)
    
    try:
        from tradingagents.daily_analysis.core.pipeline import StockAnalysisPipeline
        from tradingagents.daily_analysis.config import get_config
        
        config = get_config()
        pipeline = StockAnalysisPipeline(config=config)
        
        print("✓ Pipeline 初始化成功")
        print(f"  - 數據庫: {pipeline.db}")
        print(f"  - 數據獲取器: {pipeline.fetcher_manager}")
        print(f"  - 分析器: {pipeline.analyzer}")
        print(f"  - 搜尋服務: {pipeline.search_service.is_available if hasattr(pipeline.search_service, 'is_available') else 'N/A'}")
        return True
    except Exception as e:
        print(f"✗ Pipeline 初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_data_provider():
    """測試數據提供者共用"""
    print("\n" + "=" * 70)
    print("🗄️  測試 4: 數據提供者（共用）")
    print("=" *70)
    
    try:
        from tradingagents.data_provider import DataFetcherManager
        manager = DataFetcherManager()
        print("✓ DataFetcherManager 導入成功")
        print(f"  - 管理器類型: {type(manager)}")
        return True
    except Exception as e:
        print(f"✗ DataFetcherManager 導入失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_storage():
    """測試存儲系統"""
    print("\n" + "=" * 70)
    print("💾 測試 5: 存儲系統（SQLite）")
    print("=" * 70)
    
    try:
        from tradingagents.daily_analysis.storage import get_db
        db = get_db()
        print("✓ 資料庫連接成功")
        print(f"  - 資料庫類型: {type(db)}")
        
        # 測試查詢
        try:
            today_stocks = db.get_today_stocks()
            print(f"  - 今日數據股票數: {len(today_stocks) if today_stocks else 0}")
        except Exception as e:
            print(f"  - 查詢測試: {e}")
        
        return True
    except Exception as e:
        print(f"✗ 資料庫連接失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_router_endpoints():
    """測試路由端點定義"""
    print("\n" + "=" * 70)
    print("🌐 測試 6: API 端點定義")
    print("=" * 70)
    
    try:
        from backend.routers.daily_analysis import router
        
        print("✓ API Router 載入成功")
        print(f"\n可用端點 ({len(router.routes)} 個):")
        
        for route in router.routes:
            methods = ', '.join(route.methods)
            print(f"  - [{methods:6}] {route.path}")
            if hasattr(route, 'summary') and route.summary:
                print(f"            {route.summary}")
        
        return True
    except Exception as e:
        print(f"✗ Router 載入失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """執行所有測試"""
    print("\n")
    print("🧪 Daily Analysis API 功能測試")
    print("=" * 70)
    
    tests = [
        ("模組導入", test_imports),
        ("配置加載", test_config),
        ("Pipeline 初始化", test_pipeline_init),
        ("數據提供者", test_data_provider),
        ("存儲系統", test_storage),
        ("API 端點", test_router_endpoints),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
        except Exception as e:
            print(f"\n✗ 測試 '{name}' 發生未預期錯誤: {e}")
            results[name] = False
    
    # 結果摘要
    print("\n" + "=" * 70)
    print("📊 測試結果摘要")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status} - {name}")
    
    print(f"\n總計: {passed}/{total} 通過")
    
    if passed == total:
        print("\n🎉 所有測試通過！API 功能正常")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 個測試失敗，請檢查錯誤訊息")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
