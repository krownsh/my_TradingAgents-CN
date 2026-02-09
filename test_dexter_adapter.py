"""
Dexter Adapter 測試腳本

測試所有 tool adapter 的基本功能。
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.dexter_adapter.tools import (
    dexter_get_price_snapshot,
    dexter_get_prices,
    dexter_get_news,
    dexter_get_income_statement
)


async def test_price_snapshot():
    """測試即時報價"""
    print("\n" + "="*60)
    print("測試: dexter_get_price_snapshot")
    print("="*60)
    
    # US 股票
    print("\n[US] AAPL 即時報價:")
    result = await dexter_get_price_snapshot("US:AAPL")
    print(f"  Quality: {result.quality}")
    print(f"  Provider: {result.source_provider}")
    print(f"  Data: {result.data}")
    print(f"  Message: {result.message}")
    
    # TW 股票
    print("\n[TW] 2330 即時報價:")
    result = await dexter_get_price_snapshot("TW:2330")
    print(f"  Quality: {result.quality}")
    print(f"  Provider: {result.source_provider}")
    print(f"  Data: {result.data}")
    print(f"  Message: {result.message}")


async def test_price_history():
    """測試歷史價格"""
    print("\n" + "="*60)
    print("測試: dexter_get_prices")
    print("="*60)
    
    # US 股票
    print("\n[US] AAPL 近 30 天價格:")
    result = await dexter_get_prices("US:AAPL")
    print(f"  Quality: {result.quality}")
    print(f"  Provider: {result.source_provider}")
    if result.data:
        print(f"  Bars Count: {result.data.get('count')}")
        print(f"  Date Range: {result.data.get('start_date')} ~ {result.data.get('end_date')}")
    print(f"  Message: {result.message}")
    
    # TW 股票
    print("\n[TW] 2330 近 30 天價格:")
    result = await dexter_get_prices("TW:2330", start_date="2024-01-01", end_date="2024-01-31")
    print(f"  Quality: {result.quality}")
    print(f"  Provider: {result.source_provider}")
    if result.data:
        print(f"  Bars Count: {result.data.get('count')}")
    print(f"  Message: {result.message}")


async def test_news():
    """測試新聞/公告"""
    print("\n" + "="*60)
    print("測試: dexter_get_news")
    print("="*60)
    
    # US 新聞
    print("\n[US] AAPL 新聞:")
    result = await dexter_get_news("US:AAPL", limit=5)
    print(f"  Quality: {result.quality}")
    print(f"  Provider: {result.source_provider}")
    if result.data:
        print(f"  News Count: {result.data.get('count')}")
    print(f"  Message: {result.message}")
    
    # TW 公告
    print("\n[TW] 2330 公告/新聞:")
    result = await dexter_get_news("TW:2330", limit=5)
    print(f"  Quality: {result.quality}")
    print(f"  Provider: {result.source_provider}")
    if result.data:
        print(f"  News Count: {result.data.get('count')}")
    print(f"  Message: {result.message}")


async def test_fundamentals():
    """測試財報"""
    print("\n" + "="*60)
    print("測試: dexter_get_income_statement")
    print("="*60)
    
    # US 財報
    print("\n[US] AAPL 損益表:")
    result = await dexter_get_income_statement("US:AAPL", period="annual", limit=3)
    print(f"  Quality: {result.quality}")
    print(f"  Provider: {result.source_provider}")
    print(f"  Has Data: {result.data is not None}")
    print(f"  Message: {result.message}")
    
    # TW 財報（預期 MISSING）
    print("\n[TW] 2330 損益表 (預期 MISSING):")
    result = await dexter_get_income_statement("TW:2330", period="annual", limit=3)
    print(f"  Quality: {result.quality}")
    print(f"  Provider: {result.source_provider}")
    print(f"  Has Data: {result.data is not None}")
    print(f"  Message: {result.message}")


async def main():
    """執行所有測試"""
    print("\n🚀 Dexter Adapter 測試開始")
    print("="*60)
    
    try:
        await test_price_snapshot()
        await test_price_history()
        await test_news()
        await test_fundamentals()
        
        print("\n" + "="*60)
        print("✅ 所有測試完成")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
