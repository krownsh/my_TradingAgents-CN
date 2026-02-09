
import asyncio
import sys
import io
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
import pandas as pd

# Fix for Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# Mock missing dependencies
sys.modules['motor'] = MagicMock()
sys.modules['motor.motor_asyncio'] = MagicMock()
sys.modules['app.core.database'] = MagicMock()
sys.modules['stockstats'] = MagicMock()

from tradingagents.models.core import SymbolKey, MarketType, TimeFrame
from tradingagents.models.stock_data_models import StockDailyQuote
from app.services.screening_service import ScreeningService, ScreeningParams

class TestScreeningService:
    async def test_run_scanner(self):
        print("\n🧪 Testing ScreeningService.run (Async)...")
        
        # Mock dependencies
        with patch('app.services.screening_service.get_dataflow_interface') as mock_get_df, \
             patch('app.services.screening_service.get_mongo_db') as mock_get_db:
            
            # Setup DataFlow Interface Mock
            mock_dataflow = MagicMock()
            mock_get_df.return_value = mock_dataflow
            
            # Mock get_bars return value
            # Create a sample quote that SHOULD pass the condition (close > 100)
            quote = StockDailyQuote(
                symbol="2330", 
                market="TW", 
                data_source="unified",
                trade_date=datetime.now().date(),
                open=100.0, high=110.0, low=90.0, close=105.0, volume=1000,
                amount=105000.0, change=5.0, pct_chg=5.0, pre_close=100.0
            )
            mock_dataflow.get_bars = AsyncMock(return_value=[quote])
            
            # Setup MongoDB Mock for _get_universe
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_collection = MagicMock()
            mock_db.stock_basic_info_global = mock_collection
            
            # Mock find return value (cursor)
            mock_cursor = [{"code": "2330"}]
            mock_collection.find.return_value = mock_cursor
            
            # Initialize Service
            service = ScreeningService()
            
            # Define conditions: Price > 100
            conditions = {
                "logic": "AND",
                "children": [
                    {"field": "close", "op": ">", "value": 100}
                ]
            }
            params = ScreeningParams(market="TW", limit=10)
            
            # Run Scanner
            # Note: ScreenService.run now accepts dictionary conditions directly from params?
            # Looking at source: 
            # def run(self, conditions: Dict[str, Any], params: ScreeningParams) -> Dict[str, Any]:
            # needed_fields = self._collect_fields_from_conditions(conditions)
            
            result = await service.run(conditions, params)
            
            print(f"DEBUG: Scanner Result: {result}")
            
            # Verify Universe Query
            mock_collection.find.assert_called_once()
            call_args = mock_collection.find.call_args
            print(f"DEBUG: MongoDB Query: {call_args[0][0]}")
            assert call_args[0][0]['market'] == "TW"
            
            # Verify DataFlow Call
            mock_dataflow.get_bars.assert_called()
            
            # results should contain the item
            items = result.get("items", [])
            print(f"DEBUG: Items returned: {len(items)}")
            assert len(items) == 1
            assert items[0]['code'] == "2330"
            print("✅ Scanner successfully found target stock")

# manual run
async def main():
    test = TestScreeningService()
    await test.test_run_scanner()

if __name__ == "__main__":
    asyncio.run(main())
