import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.getcwd())

from tradingagents.models.core import SymbolKey, MarketType, TimeFrame
from tradingagents.providers.manager import ProviderManager
from tradingagents.providers.us.yahoo import YahooFinanceProvider
from tradingagents.providers.tw.twse import TWSEProvider
from tradingagents.providers.tw.tpex import TPExProvider

async def main():
    print("🚀 Starting Provider Verification...")

    # 1. Initialize Manager
    manager = ProviderManager()
    
    # 2. Register Providers
    yahoo_provider = YahooFinanceProvider()
    twse_provider = TWSEProvider()
    tpex_provider = TPExProvider() # TPEx provider

    # Register US provider (Yahoo)
    manager.register_provider(yahoo_provider)
    
    # Register TW providers (TWSE, TPEx)
    # Note: Yahoo also supports TW, but we want to test specific providers if possible
    # But since all use yfinance backend, result should be similar
    manager.register_provider(twse_provider)
    manager.register_provider(tpex_provider)

    print("\n📋 Providers Registered:")
    for market, providers in manager.providers.items():
        print(f"  - {market.value}: {[p.provider_name for p in providers]}")

    # 3. Test US Stock (AAPL)
    print("\n🇺🇸 Testing US Stock (AAPL)...")
    aapl_key = SymbolKey(market=MarketType.US, code="AAPL")
    
    start_date = datetime.now() - timedelta(days=5)
    end_date = datetime.now()
    
    try:
        bars = await manager.get_bars(aapl_key, TimeFrame.DAILY, start_date, end_date)
        print(f"  ✅ AAPL Bars: {len(bars)} records")
        if bars:
            print(f"     Latest: {bars[-1].trade_date} Close: {bars[-1].close}")
    except Exception as e:
        print(f"  ❌ AAPL Failed: {e}")

    # 4. Test TW Stock (2330 - TWSE)
    print("\n🇹🇼 Testing TW Stock (2330 - TSMC)...")
    tsmc_key = SymbolKey(market=MarketType.TW, code="2330")
    
    try:
        bars = await manager.get_bars(tsmc_key, TimeFrame.DAILY, start_date, end_date)
        print(f"  ✅ 2330 Bars: {len(bars)} records")
        if bars:
            print(f"     Latest: {bars[-1].trade_date} Close: {bars[-1].close} Source: {bars[-1].data_source}")
    except Exception as e:
        print(f"  ❌ 2330 Failed: {e}")

    # 5. Test TW Stock (8069 - TPEx - discrete)
    # 8069 is PCL, listed on TPEx
    print("\n🇹🇼 Testing TW Stock (8069 - TPEx)...")
    pcl_key = SymbolKey(market=MarketType.TW, code="8069") # Market is still TW
    
    # ProviderManager routes to TW providers.
    # We have Yahoo (supports TW), TWSE (supports TW), TPEx (supports TW).
    # It will try them in order.
    # Implementation detail: TWSEProvider adds .TW, TPExProvider adds .TWO.
    # 8069.TW might assume it's TWSE and fail or redirect. 8069.TWO is correct for TPEx.
    # Let's see which one succeeds first.
    
    try:
        bars = await manager.get_bars(pcl_key, TimeFrame.DAILY, start_date, end_date)
        print(f"  ✅ 8069 Bars: {len(bars)} records")
        if bars:
            print(f"     Latest: {bars[-1].trade_date} Close: {bars[-1].close} Source: {bars[-1].data_source}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ❌ 8069 Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
