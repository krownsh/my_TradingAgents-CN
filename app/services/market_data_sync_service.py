import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from pymongo import UpdateOne
from app.core.database import get_mongo_db
from tradingagents.dataflows.interface_v2 import get_dataflow_interface
from app.services.unified_stock_service import UnifiedStockService
from tradingagents.models.core import MarketType, SymbolKey, TimeFrame

logger = logging.getLogger(__name__)

class MarketDataSyncService:
    """
    通用市场数据同步服务
    支持 US, TW 市场，通过 ProviderManager 获取数据。
    """

    def __init__(self):
        self.dataflow = get_dataflow_interface()
        self.db = get_mongo_db()
        self.unified_service = UnifiedStockService(self.db)

    async def sync_all_markets(self):
        """同步所有支持市场的股票列表和基础信息"""
        markets = [MarketType.US, MarketType.TW, MarketType.HK] # Explicitly supported/enabled markets
        results = {}
        for market in markets:
            res = await self.sync_market_listing(market)
            results[market.value] = res
        return results

    async def sync_market_listing(self, market: MarketType) -> Dict[str, int]:
        """
        同步特定市场的股票列表和基础信息
        1. 从 Provider 获取 Symbol 列表
        2. 获取 Basic Info
        3. Upsert 到数据库
        """
        logger.info(f"🔄 开始同步市场列表: {market}")
        
        # 1. 获取该市场的所有 Provider，并汇总 Symbol List
        # ProviderManager doesn't expose providers directly by list, 
        # but we can try to get them via registered ones using a hack or just rely on main ones.
        # Actually Interface doesn't expose `get_symbol_list` aggregation.
        # So we need to access ProviderManager from DataFlowInterface.
        
        provider_manager = self.dataflow.provider_manager
        providers = provider_manager.providers.get(market, [])
        
        if not providers:
            logger.warning(f"⚠️ 市场 {market} 没有注册的 Provider")
            return {"count": 0, "status": "no_provider"}

        all_symbols: List[SymbolKey] = []
        for provider in providers:
            try:
                symbols = await provider.get_symbol_list()
                if symbols:
                    logger.info(f"📊 Provider {provider.provider_name} 返回了 {len(symbols)} 个标的")
                    all_symbols.extend(symbols)
            except Exception as e:
                logger.error(f"❌ Provider {provider.provider_name} 获取列表失败: {e}")

        unique_symbols = {s.code: s for s in all_symbols}.values()
        
        logger.info(f"📊 市场 {market} 总计待同步标的: {len(unique_symbols)}")
        
        collection_name = self.unified_service.collection_map.get(market.value, {}).get("basic_info")
        if not collection_name:
            logger.error(f"❌ 市场 {market} 没有配置对应的集合")
            return {"count": 0, "status": "no_collection"}

        updated_count = 0
        inserted_count = 0
        
        # 2. 批量处理
        semaphore = asyncio.Semaphore(10)

        async def fetch_enrich(symbol: SymbolKey):
            async with semaphore:
                try:
                    # 获取详细的基础信息
                    basic_info = await self.dataflow.get_basic_info(symbol)
                    if basic_info:
                        if hasattr(basic_info, 'model_dump'):
                             d = basic_info.model_dump()
                        else:
                             d = dict(basic_info)
                        d["updated_at"] = datetime.utcnow()
                        d["source"] = d.get("data_source", "unified")
                        # Ensure 'code' exists (use symbol if missing)
                        if "code" not in d and "symbol" in d:
                            d["code"] = d["symbol"]
                        return d
                except Exception as e:
                    logger.warning(f"⚠️ 获取 {symbol} 基础信息失败: {e}")
                
                # Fallback to minimal info
                return {
                    "market": market.value,
                    "code": symbol.code,
                    "symbol": symbol.code,
                    "updated_at": datetime.utcnow(),
                    "source": "listing"
                }

        tasks = [fetch_enrich(s) for s in unique_symbols]
        results = await asyncio.gather(*tasks)

        ops = []
        for doc in results:
            ops.append(
                UpdateOne(
                    {"code": doc["code"], "source": doc["source"]},
                    {"$set": doc},
                    upsert=True
                )
            )

        if ops:
            try:
                res = await self.db[collection_name].bulk_write(ops)
                updated_count = res.modified_count
                inserted_count = res.upserted_count
                logger.info(f"✅ 市场 {market} 同步完成: 新增 {inserted_count}, 更新 {updated_count}")
            except Exception as e:
                logger.error(f"❌ 批量写入失败: {e}")
                # Log a sample doc for debugging
                if results:
                    logger.error(f"Sample doc: {results[0]}")
        
        return {"updated": updated_count, "inserted": inserted_count}


    async def sync_quotes(self, market: MarketType) -> Dict[str, int]:
        """
        同步实时行情 (Snapshot)
        """
        logger.info(f"🔄 开始同步行情: {market}")
        
        # 1. 获取所有通过 sync_market_listing 存入 DB 的 symbols
        basic_collection = self.unified_service.collection_map.get(market.value, {}).get("basic_info")
        quotes_collection = self.unified_service.collection_map.get(market.value, {}).get("quotes")
        
        if not basic_collection or not quotes_collection:
            logger.error(f"❌ 市场 {market} 没有配置对应的集合")
            return {"count": 0, "status": "no_collection"}

        cursor = self.db[basic_collection].find({"market": market.value}, {"code": 1})
        
        codes = []
        async for doc in cursor:
            codes.append(doc['code'])
            
        if not codes:
            logger.warning(f"⚠️ 数据库中没有市场 {market} 的标的，请先运行列表同步")
            return {"updated": 0, "inserted": 0, "status": "no_symbols"}
            
        logger.info(f"📊 市场 {market} 需同步行情: {len(codes)}")
        
        ops = []
        failed_count = 0
        
        semaphore = asyncio.Semaphore(10) # Limit concurrency
        
        async def fetch_and_prep(code):
            async with semaphore:
                try:
                    s = SymbolKey(market=market, code=code)
                    quote = await self.dataflow.get_quote(s)
                    if quote:
                        return quote
                except Exception as e:
                    # logger.debug(f"Failed to get quote for {code}: {e}")
                    pass
                return None

        tasks = [fetch_and_prep(code) for code in codes]
        
        chunk_size = 50
        updated_count = 0
        inserted_count = 0
        
        for i in range(0, len(tasks), chunk_size):
            chunk = tasks[i:i+chunk_size]
            results = await asyncio.gather(*chunk)
            
            chunk_ops = []
            for q in results:
                if q:
                    if hasattr(q, 'model_dump'):
                         d = q.model_dump()
                    else:
                         d = dict(q)
                    d['market'] = market.value
                    # upsert key: market + symbol
                    chunk_ops.append(
                        UpdateOne(
                            {"code": q.symbol}, # Changed to code for consistency with CN
                            {"$set": d},
                            upsert=True
                        )
                    )
                else:
                    failed_count += 1
            
            if chunk_ops:
                try:
                    res = await self.db[quotes_collection].bulk_write(chunk_ops)
                    updated_count += res.modified_count
                    inserted_count += res.upserted_count
                except Exception as e:
                    logger.error(f"Batch write failed: {e}")
            
        logger.info(f"✅ 市场 {market} 行情同步完成: 更新{updated_count}, 新增{inserted_count}, 失败{failed_count}")
        return {"updated": updated_count, "inserted": inserted_count, "failed": failed_count}

    async def sync_daily_bars(self, market: MarketType, days: int = 3650):
        """
        同步日线数据 (Historical Bars)
        Args:
            market: 市场
            days: 同步天数，默认10年
        """
        logger.info(f"💾 开始同步日线数据: {market}, 最近 {days} 天")
        
        # 1. Get symbols from DB
        basic_collection = self.unified_service.collection_map.get(market.value, {}).get("basic_info")
        daily_collection = self.unified_service.collection_map.get(market.value, {}).get("daily")
        
        if not basic_collection or not daily_collection:
            logger.error(f"❌ 市场 {market} 没有配置对应的集合")
            return {"count": 0, "status": "no_collection"}

        cursor = self.db[basic_collection].find({"market": market.value}, {"code": 1})
        codes = []
        async for doc in cursor:
            codes.append(doc['code'])
            
        if not codes:
            logger.warning(f"⚠️ 数据库中没有市场 {market} 的标的，请先运行列表同步")
            return {"updated": 0, "inserted": 0, "status": "no_symbols"}
            
        logger.info(f"📊 市场 {market} 需同步K线: {len(codes)}")
        
        # 2. Time range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 3. Concurrency
        semaphore = asyncio.Semaphore(5) # Lower concurrency for heavy historical data
        
        updated_count = 0
        inserted_count = 0
        failed_count = 0
        
        async def fetch_and_save(code):
            async with semaphore:
                try:
                    s = SymbolKey(market=market, code=code)
                    # Use get_bars from dataflow
                    bars = await self.dataflow.get_bars(s, timeframe=TimeFrame.DAILY, start_date=start_date, end_date=end_date)
                    
                    if not bars:
                        return 0, 0, 1 # updated, inserted, failed
                    
                    ops = []
                    for bar in bars:
                        if hasattr(bar, 'model_dump'):
                             d = bar.model_dump()
                        else:
                             d = dict(bar)
                        
                        d['market'] = market.value
                        d['data_source'] = 'unified' 
                        
                        # Date handling
                        if isinstance(d['trade_date'], str):
                             d['trade_date'] = datetime.fromisoformat(d['trade_date'])
                        elif isinstance(d['trade_date'], date):
                             d['trade_date'] = datetime.combine(d['trade_date'], datetime.min.time())
                             
                        d['period'] = 'daily'
                        d['symbol'] = code 
                        
                        ops.append(
                            UpdateOne(
                                {
                                    "symbol": code, 
                                    "market": market.value, 
                                    "trade_date": d['trade_date'],
                                    "period": "daily"
                                },
                                {"$set": d},
                                upsert=True
                            )
                        )
                        
                    if ops:
                        res = await self.db[daily_collection].bulk_write(ops)
                        return res.modified_count, res.upserted_count, 0
                    return 0, 0, 0
                    
                except Exception as e:
                    logger.error(f"❌ K线同步失败 {code}: {e}")
                    return 0, 0, 1

        tasks = [fetch_and_save(code) for code in codes]
        
        # Chunking
        chunk_size = 20
        total_tasks = len(tasks)
        
        for i in range(0, total_tasks, chunk_size):
            chunk = tasks[i:i+chunk_size]
            results = await asyncio.gather(*chunk)
            
            for u, i_cnt, f in results:
                updated_count += u
                inserted_count += i_cnt
                failed_count += f
                
            logger.info(f"进度: {min(i+chunk_size, total_tasks)}/{total_tasks}")

        logger.info(f"✅ 市场 {market} 日线同步完成: 更新{updated_count}, 新增{inserted_count}, 失败{failed_count}")
        return {"updated": updated_count, "inserted": inserted_count, "failed": failed_count}


# Global Instance
_market_sync_service = None

def get_market_sync_service() -> MarketDataSyncService:
    global _market_sync_service
    if not _market_sync_service:
        _market_sync_service = MarketDataSyncService()
    return _market_sync_service

# ==================== APScheduler Tasks ====================

async def run_market_listing_sync(market_str: str = "US"):
    """
    APScheduler 任务: 同步市场列表和基础信息
    Args:
        market_str: 市场代码 (US, TW, CN, HK)
    """
    try:
        service = get_market_sync_service()
        # Handle simple string input from scheduler
        market = MarketType(market_str)
        result = await service.sync_market_listing(market)
        logger.info(f"✅ Market Listing Sync ({market_str}): {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Market Listing Sync Failed ({market_str}): {e}")
        return {"status": "error", "error": str(e)}

async def run_market_quotes_sync(market_str: str = "US"):
    """
    APScheduler 任务: 同步实时行情 (Snapshot)
    Args:
        market_str: 市场代码 (US, TW, CN, HK)
    """
    try:
        service = get_market_sync_service()
        market = MarketType(market_str)
        result = await service.sync_quotes(market)
        logger.info(f"✅ Market Quotes Sync ({market_str}): {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Market Quotes Sync Failed ({market_str}): {e}")
        return {"status": "error", "error": str(e)}

async def run_market_daily_bars_sync(market_str: str = "US", days: int = 5):
    """
    APScheduler 任务: 同步日线数据 (Historical)
    Args:
        market_str: 市场代码
        days: 同步天数 (增量更新通常较短，如5天)
    """
    try:
        service = get_market_sync_service()
        market = MarketType(market_str)
        result = await service.sync_daily_bars(market, days=days)
        logger.info(f"✅ Market Bars Sync ({market_str}): {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Market Bars Sync Failed ({market_str}): {e}")
        return {"status": "error", "error": str(e)}
