
import asyncio
import sys
import io
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, date

# Fix for Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Mock dependencies BEFORE importing agent_utils
sys.modules['tradingagents.dataflows.interface'] = MagicMock()
sys.modules['tradingagents.default_config'] = MagicMock()
# Mock ChromaDB
mock_chromadb = MagicMock()
sys.modules['chromadb'] = mock_chromadb
sys.modules['chromadb.config'] = MagicMock()
sys.modules['dashscope'] = MagicMock()
# Mock LangChain OpenAI
mock_lc_openai = MagicMock()
sys.modules['langchain_openai'] = mock_lc_openai
mock_lc_openai.ChatOpenAI = MagicMock()

# Mock LangChain Core hierarchy
# IMPORTANT: @tool decorator must be pass-through
def pass_through_decorator(func=None, **kwargs):
    if func and callable(func):
        return func
    def _dec(f):
        return f
    return _dec

mock_langchain_core = MagicMock()
sys.modules['langchain_core'] = mock_langchain_core
sys.modules['langchain_core.messages'] = MagicMock()
sys.modules['langchain_core.prompts'] = MagicMock()

mock_tools = MagicMock()
sys.modules['langchain_core.tools'] = mock_tools
mock_tools.tool = pass_through_decorator

# Mock log_tool_call
sys.modules['tradingagents.utils.logging_manager'] = MagicMock()
def mock_log_tool_call(**kwargs):
    return pass_through_decorator
sys.modules['tradingagents.utils.logging_manager'].log_tool_call = mock_log_tool_call

sys.modules['langchain_core.output_parsers'] = MagicMock()
sys.modules['langchain_core.runnables'] = MagicMock()

# Mock LangGraph hierarchy
mock_langgraph = MagicMock()
sys.modules['langgraph'] = mock_langgraph
sys.modules['langgraph.prebuilt'] = MagicMock()
sys.modules['langgraph.graph'] = MagicMock()
sys.modules['langgraph.checkpoint'] = MagicMock()
# Also langgraph.graph.message
sys.modules['langgraph.graph.message'] = MagicMock()

# Mocking strategy:
# We need to block the real tradingagents.dataflows from loading because its __init__.py 
# imports complex dependencies we want to avoid or mock.
# We must mock the package AND the submodules.

mock_dataflows_pkg = MagicMock()
sys.modules['tradingagents.dataflows'] = mock_dataflows_pkg

mock_interface = MagicMock()
sys.modules['tradingagents.dataflows.interface'] = mock_interface

mock_optimized = MagicMock()
sys.modules['tradingagents.dataflows.optimized_china_data'] = mock_optimized

# Mock DataFlowInterface v2
mock_dataflow_class = MagicMock()
mock_interface_v2 = MagicMock()
sys.modules['tradingagents.dataflows.interface_v2'] = mock_interface_v2
mock_interface_v2.DataFlowInterface = mock_dataflow_class

# Define Models for Mocks
class MockSymbolKey:
    def __init__(self, market, code):
        self.market = market
        self.code = code
    def __repr__(self):
        return f"SymbolKey(market={self.market}, code={self.code})"

class MockStockDailyQuote:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def model_dump(self):
        return self.__dict__

sys.modules['tradingagents.dataflows.interface_v2'].SymbolKey = MockSymbolKey
sys.modules['tradingagents.dataflows.interface_v2'].MarketType = MagicMock()
sys.modules['tradingagents.dataflows.interface_v2'].MarketType.CN = "CN"
sys.modules['tradingagents.dataflows.interface_v2'].MarketType.HK = "HK"
sys.modules['tradingagents.dataflows.interface_v2'].MarketType.US = "US"
sys.modules['tradingagents.dataflows.interface_v2'].TimeFrame = MagicMock()
sys.modules['tradingagents.dataflows.interface_v2'].TimeFrame.DAILY = "1d"

# Now import the module under test
from tradingagents.agents.utils.agent_utils import Toolkit

class TestStrategyEngine:
    def setup_mocks(self):
        self.mock_dataflow_instance = MagicMock()
        mock_dataflow_class.return_value = self.mock_dataflow_instance
        
        # Mock StockUtils
        self.stock_utils_patcher = patch('tradingagents.utils.stock_utils.StockUtils')
        self.mock_stock_utils = self.stock_utils_patcher.start()

    def teardown_mocks(self):
        self.stock_utils_patcher.stop()

    async def test_get_stock_market_data_unified_cn(self):
        print("\n🧪 Testing get_stock_market_data_unified (CN)...")
        self.setup_mocks()
        
        # Setup Market Info
        self.mock_stock_utils.get_market_info.return_value = {
            'is_china': True, 'is_hk': False, 'is_us': False,
            'market_name': 'A股', 'currency_name': '人民币', 'currency_symbol': '¥'
        }
        
        # Setup DataFlow Response
        quote_data = {
            'symbol': '600519',
            'date': datetime(2023, 10, 27),
            'open': 1600.0,
            'high': 1650.0,
            'low': 1590.0,
            'close': 1630.0,
            'vol': 10000,
            'pct_chg': 1.5,
            'amount': 16000000.0
        }
        quote = MockStockDailyQuote(**quote_data)
        
        # Mock async get_bars
        self.mock_dataflow_instance.get_bars = AsyncMock(return_value=[quote])

        # Debug tool itself
        debug_info = []
        debug_info.append(f"DEBUG: Toolkit.get_stock_market_data_unified type: {type(Toolkit.get_stock_market_data_unified)}")
        debug_info.append(f"DEBUG: Is MagicMock? {isinstance(Toolkit.get_stock_market_data_unified, MagicMock)}")

        # Execute in thread to avoid event loop conflict (since tool creates its own loop)
        result = await asyncio.to_thread(Toolkit.get_stock_market_data_unified, "600519", "2023-10-27", "2023-10-27")
        
        debug_info.append(f"DEBUG: Result type: {type(result)}")
        debug_info.append(f"DEBUG: Result value: {result}")
        
        with open("verify_strategy_result.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(debug_info))
        
        print(f"DEBUG: Debug info written to file")
        sys.stdout.flush()
        
        # Verify
        if not isinstance(result, str) or "A股市场数据" not in result:
             print(f"FAILURE: Expected 'A股市场数据' in result. Got type {type(result)} value {result}")
        assert isinstance(result, str)
        assert "A股市场数据" in result
        
        self.teardown_mocks()
        print("✅ CN Market Data Test Passed")

    async def test_get_stock_fundamentals_unified_cn(self):
        print("\n🧪 Testing get_stock_fundamentals_unified (CN Price Check)...")
        self.setup_mocks()
        
        # Setup Market Info
        self.mock_stock_utils.get_market_info.return_value = {
            'is_china': True, 'is_hk': False, 'is_us': False,
            'market_name': 'A股', 'currency_name': '人民币', 'currency_symbol': '¥'
        }
        
        # Setup DataFlow Response (Latest 2 days)
        quote_data = {
            'symbol': '600519',
            'date': datetime(2023, 10, 27),
            'open': 1600.0,
            'high': 1650.0,
            'low': 1590.0,
            'close': 1630.0,
            'vol': 10000,
            'pct_chg': 1.5
        }
        quote = MockStockDailyQuote(**quote_data)
        
        # Mock async get_bars
        self.mock_dataflow_instance.get_bars = AsyncMock(return_value=[quote])

        # Execute
        # Note: fundamentals tool calls internal methods which might need extensive mocking
        # We focus on verifying the "current price" part which we modified
        with patch('tradingagents.dataflows.optimized_china_data.OptimizedChinaDataProvider') as mock_provider:
             mock_provider_instance = MagicMock()
             mock_provider.return_value = mock_provider_instance
             mock_provider_instance._generate_fundamentals_report.return_value = "Mock Fundamentals Report"
             
             # Execute in thread
             result = await asyncio.to_thread(Toolkit.get_stock_fundamentals_unified, "600519", curr_date="2023-10-27")
             
             print(f"DEBUG: Result Summary:\n{result[:200]}...")
             sys.stdout.flush()
             
             with open("verify_fundamentals_result.txt", "w", encoding="utf-8") as f:
                 f.write(result)
             
             print(f"DEBUG: Fundamentals info written to file")
             sys.stdout.flush()
             
             # Verify Price Section
             if "A股当前价格信息" not in result:
                 print(f"FAILURE: Expected 'A股当前价格信息' in result. Got type {type(result)} value {result}")

             assert "A股当前价格信息" in result
             assert "1630.0" in result
             assert "Mock Fundamentals Report" in result
             
        self.teardown_mocks()
        print("✅ CN Fundamentals Price Test Passed")

async def main():
    test = TestStrategyEngine()
    await test.test_get_stock_market_data_unified_cn()
    await test.test_get_stock_fundamentals_unified_cn()

if __name__ == "__main__":
    asyncio.run(main())
