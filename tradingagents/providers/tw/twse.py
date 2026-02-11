import logging
from typing import List, Optional
from datetime import datetime
import pandas as pd
import yfinance as yf

from tradingagents.models.core import SymbolKey, TimeFrame, MarketType
from tradingagents.models.stock_data_models import StockDailyQuote, StockBasicInfo, StockRealtimeQuote, StockNews, NewsCategory
from tradingagents.providers.interfaces import MarketDataProvider

logger = logging.getLogger(__name__)

class TWSEProvider(MarketDataProvider):
    """
    台湾证券交易所 (TWSE) 数据提供者 (MVP版)
    目前底层使用 yfinance 作为数据源，后续替换为 TWSE OpenAPI。
    """

    def __init__(self):
        super().__init__("twse")

    @property
    def supported_markets(self) -> List[MarketType]:
        return [MarketType.TW]

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
        """获取历史数据 (TWSE)"""
        if symbol.market != MarketType.TW:
            return []
            
        # TWSE stocks on Yahoo used to have .TW suffix
        # But we should double check if the symbol is actually listed on TWSE
        # For now, we assume ALL TW stocks passed here are TWSE if not specified otherwise
        
        ticker = f"{symbol.code}.TW"
        
        try:
            # Reusing yfinance logic - in a real implementation this would call self._fetch_from_openapi(...)
            interval = timeframe.value if hasattr(timeframe, 'value') else timeframe
            
            df = yf.download(
                tickers=ticker, 
                start=start, 
                end=end, 
                interval=interval, 
                progress=False,
                auto_adjust=False
            )
            
            if df.empty:
                return []
            
            df = df.reset_index()            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]
            
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
                        amount=0.0,
                        pct_chg=0.0,
                        change=0.0,
                        pre_close=0.0,
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
        """获取实时行情 (TWSE)"""
        try:
            ticker = f"{symbol.code}.TW"
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.fast_info
            
            if not info or not hasattr(info, 'last_price'):
                 info = yf_ticker.info
                 price = info.get('currentPrice', info.get('regularMarketPrice'))
            else:
                 price = info.last_price
            
            if price is None:
                return None
                
            return StockRealtimeQuote(
                symbol=symbol.code,
                name=symbol.code,
                current_price=price,
                pre_close=info.previous_close if hasattr(info, 'previous_close') else 0.0,
                open=info.open if hasattr(info, 'open') else 0.0,
                high=info.day_high if hasattr(info, 'day_high') else 0.0,
                low=info.day_low if hasattr(info, 'day_low') else 0.0,
                change=0.0,
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
        return []

    async def get_symbol_list(self) -> List[SymbolKey]:
        """
        获取 TWSE 股票列表 (从 isin.twse.com.tw)
        """
        try:
            url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
            import requests
            import pandas as pd
            from io import StringIO
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            res = requests.get(url, headers=headers)
            
            if res.status_code != 200:
                return []

            dfs = pd.read_html(StringIO(res.text))
            if not dfs:
                return []
            
            df = dfs[0]
            symbols = []
            
            # Reset cache
            self._name_cache = {}
            
            start_idx = 0
            for idx, row in df.iterrows():
                if isinstance(row[0], str) and "有價證券代號及名稱" in row[0]:
                    start_idx = idx + 1
                    break
            
            for idx, row in df.iloc[start_idx:].iterrows():
                val = row[0]
                if not isinstance(val, str):
                    continue
                    
                parts = val.split()
                if len(parts) >= 2:
                    code = parts[0]
                    name = parts[1]
                    # Simple filter: TWSE stocks are usually 4 digits
                    if len(code) == 4 and code.isdigit():
                        symbols.append(SymbolKey(market=MarketType.TW, code=code))
                        self._name_cache[code] = {
                            "name": name,
                            "industry": row[4] if len(row) > 4 else "Unknown",
                            "list_date": row[2] if len(row) > 2 else None
                        }
            
            return symbols

        except Exception as e:
            logger.error(f"Error fetching TWSE list: {e}")
            return []

    async def get_basic_info(self, symbol: SymbolKey) -> Optional[StockBasicInfo]:
        """獲取基礎信息 (TWSE)"""
        # Try cache first
        if hasattr(self, '_name_cache') and symbol.code in self._name_cache:
            info = self._name_cache[symbol.code]
            return StockBasicInfo(
                symbol=symbol.code,
                exchange_symbol=f"{symbol.code}.TW",
                name=info["name"],
                market="TWSE",
                board="Main Board",
                industry=info["industry"],
                sector="Unknown",
                area="Taiwan",
                data_source=self.provider_name
            )

        # Fallback to yfinance if not in cache
        try:
            ticker_symbol = f"{symbol.code}.TW"
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            
            if not info:
                return None
                
            return StockBasicInfo(
                symbol=symbol.code,
                exchange_symbol=ticker_symbol,
                name=info.get('longName', info.get('shortName', symbol.code)),
                market="TWSE",
                board="Main Board",
                industry=info.get('industry', 'Unknown'),
                sector=info.get('sector', 'Unknown'),
                area="Taiwan",
                data_source=self.provider_name
            )
        except Exception as e:
            logger.error(f"Failed to get basic info for {symbol}: {e}")
            return None

    async def get_news(self, symbol: SymbolKey, limit: int = 10, **kwargs) -> List[StockNews]:
        """獲取新聞 (TWSE/Yahoo)"""
        import yfinance as yf
        from datetime import datetime
        from tradingagents.models.stock_data_models import StockNews, NewsCategory
        
        try:
            ticker_symbol = f"{symbol.code}.TW"
            ticker = yf.Ticker(ticker_symbol)
            news = ticker.news
            
            result = []
            for item in news[:limit]:
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
        """獲取股票情緒分析數據 (台灣市場)"""
        curr_date = datetime.now().strftime("%Y-%m-%d")
        
        sentiment_summary = f"""## 台灣市場情緒分析

**股票**: {symbol.code} (台灣證券交易所)
**分析日期**: {curr_date}

### 市場情緒概況
- 目前台灣市場社交媒體情緒數據源（如 PTT Stock 版、Dcard 財經版）暫未完全集成。
- 建議關注工商時報、經濟日報等本地財經媒體的報導熱度。

### 情緒指標
- 整體情緒: 中性
- 討論熱度: 待分析
- 投資者信心: 待評估

*注：完整的台灣社交媒體情緒分析功能正在開發中*
"""
        return sentiment_summary
