import asyncio
import logging
import sys
import io
import traceback
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

# Force UTF-8 for stdout/stderr to handle emojis on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Mock database before importing service if possible, or patch after
# We need to mock app.core.database.get_mongo_db returns a mock db
sys.modules['app.core.database'] = MagicMock()
sys.modules['app.core.database'].get_mongo_db = MagicMock(return_value=AsyncMock())

# Also mock app.core.config.settings
sys.modules['app.core.config'] = MagicMock()
sys.modules['app.core.config'].settings = MagicMock()

from app.services.market_data_sync_service import MarketDataSyncService
from tradingagents.models.core import MarketType

async def main():
    logger.info("🚀 Starting Market Sync Verification...")

    # Initialize Service
    service = MarketDataSyncService()
    
    # Mock DB collection bulk_write
    mock_db = AsyncMock()
    mock_collection = AsyncMock()
    mock_collection.bulk_write.return_value = MagicMock(modified_count=10, upserted_count=5)
    
    # IMPORTANT: find returns a cursor (AsyncIterator), it is NOT awaitable itself.
    # So find must be a MagicMock, not AsyncMock.
    mock_collection.find = MagicMock()
    
    mock_db.stock_basic_info_global = mock_collection
    service.db = mock_db

    # Test US Sync
    logger.info("\n--------------------------------------------------")
    logger.info("Testing US Market Sync...")
    try:
        result_us = await service.sync_market_listing(MarketType.US)
        logger.info(f"🇺🇸 US Sync Result: {result_us}")
    except Exception as e:
        logger.error(f"❌ US Sync Failed: {e}", exc_info=True)

    # Test TW Sync
    logger.info("\n--------------------------------------------------")
    logger.info("Testing TW Market Sync...")
    try:
        result_tw = await service.sync_market_listing(MarketType.TW)
        logger.info(f"🇹🇼 TW Sync Result: {result_tw}")
    except Exception as e:
        logger.error(f"❌ TW Sync Failed: {e}", exc_info=True)

    # Test Quotes Sync (US)
    # We need to populate the mock DB first so sync_quotes finds symbols
    # Mock 'find' to return a FRESH iterator each time
    mock_db.stock_basic_info_global.find.side_effect = lambda *args, **kwargs: AsyncIterator([
        {'code': 'AAPL', 'market': 'US'}, 
        {'code': 'NVDA', 'market': 'US'},
        {'code': '2330', 'market': 'TW'} # Add TW code for daily bars test
    ])
    
    logger.info("\n--------------------------------------------------")
    logger.info("Testing US Quotes Sync...")
    try:
        result_q = await service.sync_quotes(MarketType.US)
        logger.info(f"📈 US Quotes Sync Result: {result_q}")
    except Exception as e:
        logger.error(f"❌ Quotes Sync Failed: {e}")
        traceback.print_exc()

    # Test Daily Bars Sync (TW)
    
    mock_bar = MagicMock()
    mock_bar.model_dump.return_value = {
        'symbol': '2330', 'trade_date': datetime(2023, 1, 1), 
        'open': 500.0, 'high': 510.0, 'low': 490.0, 'close': 505.0, 'volume': 1000
    }
    # Ensure trade_date is datetime as expected by logic
    
    # We need to mock the get_bars method of the DataFlowInterface instance inside service
    service.dataflow.get_bars = AsyncMock(return_value=[mock_bar])
    
    logger.info("\n--------------------------------------------------")
    logger.info("Testing TW Daily Bars Sync...")
    try:
        # Sync last 5 days
        result_bars = await service.sync_daily_bars(MarketType.TW, days=5)
        logger.info(f"📅 TW Bars Sync Result: {result_bars}")
    except Exception as e:
        logger.error(f"❌ TW Bars Sync Failed: {e}")
        traceback.print_exc()

    # Verify what was passed to DB
    logger.info("\n--------------------------------------------------")
    logger.info("Verification of DB Operations:")
    
    # Check calls on basic info
    calls = mock_collection.bulk_write.call_args_list
    logger.info(f"📊 Stock Basic Info calls: {len(calls)}")
    
    # Check calls on quotes
    # quotes service uses db.market_quotes_global
    mock_quotes = mock_db.market_quotes_global
    q_calls = mock_quotes.bulk_write.call_args_list
    logger.info(f"📈 Market Quotes calls: {len(q_calls)}")

    # Check calls on daily bars
    mock_bars = mock_db.stock_daily_quotes
    b_calls = mock_bars.bulk_write.call_args_list
    logger.info(f"📅 Daily Bars calls: {len(b_calls)}")
    
    if len(b_calls) > 0:
        args_b, _ = b_calls[0]
        logger.info(f"   Sample Bar Op: {args_b[0][0]}")

class AsyncIterator:
    def __init__(self, items):
        self.items = items
    def __aiter__(self):
        return self
    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)

if __name__ == "__main__":
    asyncio.run(main())
