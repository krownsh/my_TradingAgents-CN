#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
記憶管理系統 (Memory System)
負責股票分檔記憶：Key Facts、Rolling Summaries 與歷史對話存儲
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from tradingagents.config.database_manager import get_mongodb_client

logger = logging.getLogger(__name__)

class MemoryMgr:
    """股票分檔記憶管理器"""
    
    def __init__(self):
        self.client = get_mongodb_client()
        self.db = self.client.get_database('tradingagents') if self.client else None
        self.facts_col = self.db.stock_memory_facts if self.db is not None else None
        self.summaries_col = self.db.stock_memory_summaries if self.db is not None else None

    def save_key_fact(self, symbol_key: str, content: str, source: str = "meeting"):
        """保存關鍵事實"""
        if self.facts_col is None: return
        
        self.facts_col.update_one(
            {"symbol_key": symbol_key, "content": content},
            {
                "$set": {
                    "symbol_key": symbol_key,
                    "content": content,
                    "source": source,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )

    def get_key_facts(self, symbol_key: str, limit: int = 10) -> List[str]:
        """獲取關鍵事實"""
        if self.facts_col is None: return []
        
        cursor = self.facts_col.find({"symbol_key": symbol_key}).sort("updated_at", -1).limit(limit)
        return [doc["content"] for doc in cursor]

    def update_rolling_summary(self, symbol_key: str, new_summary: str):
        """更新滾動摘要"""
        if self.summaries_col is None: return
        
        self.summaries_col.update_one(
            {"symbol_key": symbol_key},
            {
                "$set": {
                    "symbol_key": symbol_key,
                    "summary": new_summary,
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )

    def get_rolling_summary(self, symbol_key: str) -> Optional[str]:
        """獲取滾動摘要"""
        if self.summaries_col is None: return None
        
        doc = self.summaries_col.find_one({"symbol_key": symbol_key})
        return doc["summary"] if doc else None
