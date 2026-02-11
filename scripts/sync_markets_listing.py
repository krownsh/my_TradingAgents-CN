import asyncio
import logging
import sys
from app.core.database import init_database, get_mongo_db
from app.services.market_data_sync_service import get_market_sync_service
from tradingagents.models.core import MarketType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """
    Main entry point for synchronizing TW and US market listings.
    """
    logger.info("🚀 Starting Market Data Synchronization...")
    
    # Initialize database
    await init_database()
    
    # Get synchronization service
    service = get_market_sync_service()
    
    # Sync Taiwan Markets (TWSE/TPEx)
    logger.info("🔄 Synchronizing TW market listing (TWSE/TPEx)...")
    tw_res = await service.sync_market_listing(MarketType.TW)
    logger.info(f"✅ TW Result: {tw_res}")
    
    # Sync US Markets (Yahoo Finance)
    logger.info("🔄 Synchronizing US market listing (yfinance)...")
    us_res = await service.sync_market_listing(MarketType.US)
    logger.info(f"✅ US Result: {us_res}")
    
    logger.info("✨ Market Data Synchronization Completed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"❌ Synchronization Script Failed: {e}")
        sys.exit(1)
