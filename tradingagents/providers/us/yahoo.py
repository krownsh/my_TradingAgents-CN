import logging
from typing import List, Optional
from datetime import datetime
import pandas as pd
import yfinance as yf

from tradingagents.models.core import SymbolKey, TimeFrame, MarketType
from tradingagents.models.stock_data_models import StockDailyQuote, StockBasicInfo, StockRealtimeQuote, StockNews, NewsCategory, SentimentType
from tradingagents.providers.interfaces import MarketDataProvider

logger = logging.getLogger(__name__)

class YahooFinanceProvider(MarketDataProvider):
    """
    Yahoo Finance 数据提供者
    支持 US, TW, HK 等多个市场。
    """

    def __init__(self):
        super().__init__("yfinance")

    @property
    def supported_markets(self) -> List[MarketType]:
        return [MarketType.US, MarketType.TW, MarketType.HK]

    async def connect(self) -> bool:
        self.connected = True
        return True

    async def disconnect(self):
        self.connected = False

    async def get_bars(
        self, 
        symbol: SymbolKey, 
        timeframe: TimeFrame, 
        start: datetime, 
        end: datetime
    ) -> List[StockDailyQuote]:
        """获取历史K线数据"""
        try:
            ticker_symbol = self._convert_symbol(symbol)
            
            # yfinance interval mapping
            # TimeFrame enum values align with yfinance mostly
            interval = timeframe.value if hasattr(timeframe, 'value') else timeframe
            
            # Download data
            df = yf.download(
                tickers=ticker_symbol, 
                start=start, 
                end=end, 
                interval=interval, 
                progress=False,
                auto_adjust=False  # Keep raw OHLC
            )
            
            if df.empty:
                return []
            
            # Reset index to make Date a column
            df = df.reset_index()
            
            # Standardize columns (lowercase)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]
            
            # Transform to StockDailyQuote objects
            results = []
            for _, row in df.iterrows():
                try:
                    quote = StockDailyQuote(
                        symbol=symbol.code,
                        trade_date=row['date'].date(),
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume'],
                        amount=0.0, # Yahoo doesn't provide amount usually
                        pct_chg=0.0, # Need to calculate or ignore
                        change=0.0,
                        pre_close=0.0, # Need to calculate
                        data_source=self.provider_name
                    )
                    results.append(quote)
                except Exception as e:
                    logger.warning(f"Error parsing row: {e}")
                    continue
            
            return results

        except Exception as e:
            logger.error(f"Failed to get bars for {symbol}: {e}")
            return []

    async def get_quote(self, symbol: SymbolKey) -> Optional[StockRealtimeQuote]:
        """获取实时行情"""
        try:
            ticker_symbol = self._convert_symbol(symbol)
            ticker = yf.Ticker(ticker_symbol)
            # Use fast_info for realtime/delayed quote if available, else info
            info = ticker.fast_info
            
            if not info or not hasattr(info, 'last_price'):
                 # Fallback to .info (slower)
                 info = ticker.info
                 price = info.get('currentPrice', info.get('regularMarketPrice'))
            else:
                 price = info.last_price
            
            if price is None:
                return None
                
            return StockRealtimeQuote(
                symbol=symbol.code,
                name=symbol.code, # Might need extra fetch for name
                current_price=price,
                pre_close=info.previous_close if hasattr(info, 'previous_close') else 0.0,
                open=info.open if hasattr(info, 'open') else 0.0,
                high=info.day_high if hasattr(info, 'day_high') else 0.0,
                low=info.day_low if hasattr(info, 'day_low') else 0.0,
                change=0.0, # Calculate if needed
                pct_chg=0.0,
                volume=info.last_volume if hasattr(info, 'last_volume') else 0.0,
                amount=0.0,
                timestamp=datetime.now(),
                data_source=self.provider_name
            )

        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None

    async def search_symbol(self, query: str) -> List[SymbolKey]:
        """Yahoo Finance generally doesn't expose a clean search API via yfinance lib"""
        return []

    async def get_basic_info(self, symbol: SymbolKey) -> Optional[StockBasicInfo]:
        """获取基础信息"""
        try:
            ticker_symbol = self._convert_symbol(symbol)
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            return StockBasicInfo(
                symbol=symbol.code,
                exchange_symbol=ticker_symbol,
                name=info.get('longName', symbol.code),
                name_en=info.get('shortName'),
                market=symbol.market,
                board="Main",
                industry=info.get('industry', 'Unknown'),
                sector=info.get('sector', 'Unknown'),
                area=info.get('country', 'Unknown'),
                currency=info.get('currency', 'USD'),
                data_source=self.provider_name
            )
        except Exception as e:
            logger.error(f"Failed to get basic info for {symbol}: {e}")
            return None

    async def get_news(self, symbol: SymbolKey, limit: int = 10, **kwargs) -> List[StockNews]:
        """获取新聞 (yfinance)"""
        import yfinance as yf
        from datetime import datetime
        from tradingagents.models.stock_data_models import StockNews, NewsCategory
        
        try:
            ticker = yf.Ticker(symbol.code)
            news = ticker.news
            
            result = []
            for item in news[:limit]:
                # Map yfinance news to StockNews model
                # Some items might not have all fields
                pub_time = datetime.fromtimestamp(item.get('providerPublishTime', 0))
                
                stock_news = StockNews(
                    symbol=symbol.code,
                    title=item.get('title', ''),
                    url=item.get('link', ''),
                    source=item.get('publisher', 'Yahoo Finance'),
                    publish_time=pub_time,
                    category=NewsCategory.MARKET_NEWS,
                    data_source="yfinance"
                )
                result.append(stock_news)
            return result
        except Exception as e:
            logger.error(f"Error fetching news for {symbol.code} from Yahoo: {e}")
            return []

    async def get_sentiment(self, symbol: SymbolKey, **kwargs) -> str:
        """获取股票情緒分析數據 (基於 Reddit)"""
        try:
            from tradingagents.dataflows.interface import get_reddit_company_news
            from datetime import datetime
            
            curr_date = datetime.now().strftime("%Y-%m-%d")
            # 獲取最近 7 天的 Reddit 內容作為情緒分析來源
            reddit_content = get_reddit_company_news(symbol.code, curr_date, look_back_days=7, max_limit_per_day=5)
            
            if not reddit_content or reddit_content.strip() == "":
                return "未找到相關 Reddit 討論內容。"
            
            return reddit_content
        except Exception as e:
            logger.error(f"Error fetching sentiment for {symbol.code} from Reddit: {e}")
            return f"❌ 獲取 Reddit 情緒數據失敗: {e}"

    async def get_symbol_list(self) -> List[SymbolKey]:
        """
        获取美股列表
        目前返回一个静态列表作为 MVP，后续可集成 Finnhub 或其他源
        """
        # US stocks
        us_stock_codes = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX",
            "JPM", "BAC", "WFC", "GS", "MS",
            "KO", "PEP", "WMT", "HD", "MCD",
            "JNJ", "PFE", "UNH", "ABBV",
            "XOM", "CVX",
            "TQQQ", "SQQQ", "SOXL", "SOXS" # ETFs
        ]
        
        # HK stocks
        hk_stock_codes = [
            "0700", "3690", "9988", "1211", "1810", "1024", "2318", "0005", "0388"
        ]
        
        symbols = []
        symbols.extend([SymbolKey(market=MarketType.US, code=code) for code in us_stock_codes])
        symbols.extend([SymbolKey(market=MarketType.HK, code=code) for code in hk_stock_codes])
        
        return symbols

    def _convert_symbol(self, symbol: SymbolKey) -> str:
        """转换通用 SymbolKey 为 Yahoo Ticker 格式"""
        code = symbol.code
        if symbol.market == MarketType.TW:
            return f"{code}.TW"
        elif symbol.market == MarketType.HK:
            # Handle numeric codes for HK (e.g. 0700 -> 0700.HK)
            return f"{int(code):04d}.HK" if code.isdigit() else f"{code}.HK"
        elif symbol.market == MarketType.CN:
            # Simple heuristic for SH/SZ
            if code.startswith('6'):
                return f"{code}.SS"
            else:
                return f"{code}.SZ"
        return code
