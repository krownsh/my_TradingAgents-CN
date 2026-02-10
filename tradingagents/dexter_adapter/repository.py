#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Research Repository - 研究數據持久化層
負責將 Dexter 的研究過程存儲至 MongoDB
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from tradingagents.models.research import ResearchEvent, ResearchSessionSummary

logger = logging.getLogger(__name__)

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

class ResearchRepository:
    """
    研究數據存儲庫
    """
    def __init__(self, connection_string: str = None, db_name: str = "tradingagents"):
        self.connection_string = connection_string or os.getenv("MONGODB_CONNECTION_STRING")
        self.db_name = db_name
        self.client = None
        self.db = None
        self._connected = False
        
        if MONGODB_AVAILABLE and self.connection_string:
            try:
                # 建立連接
                self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
                # 測試連通性
                self.client.admin.command('ping')
                self.db = self.client[self.db_name]
                self._connected = True
                
                # 確保索引
                self._ensure_indexes()
                logger.info(f"✅ ResearchRepository 已成功連接至 MongoDB: {self.db_name}")
            except Exception as e:
                logger.error(f"❌ ResearchRepository MongoDB 連接失敗: {e}")
        else:
            if not MONGODB_AVAILABLE:
                logger.warning("⚠️ pymongo 未安裝，持久化功能將失效。")
            if not self.connection_string:
                logger.warning("⚠️ MONGODB_CONNECTION_STRING 未設置。")

    def _ensure_indexes(self):
        """建立必要的索引"""
        if not self._connected:
            return
        
        try:
            self.db["research_events"].create_index([("symbol_key", 1), ("timestamp", 1)])
            self.db["research_events"].create_index("event_id", unique=True)
            self.db["research_sessions"].create_index("session_id", unique=True)
        except Exception as e:
            logger.warning(f"建立研究索引失敗: {e}")

    def save_event(self, event: ResearchEvent) -> bool:
        """存儲單個研究事件"""
        if not self._connected:
            return False
        try:
            collection = self.db["research_events"]
            data = event.dict()
            # 兼容 Pydantic 數據轉換
            if isinstance(data.get("timestamp"), datetime):
                pass # pymongo 支援 datetime
            
            collection.insert_one(data)
            return True
        except PyMongoError as e:
            logger.error(f"儲存 ResearchEvent 失敗: {e}")
            return False

    def save_session_summary(self, summary: ResearchSessionSummary) -> bool:
        """存儲或更新研究會話摘要"""
        if not self._connected:
            return False
        try:
            collection = self.db["research_sessions"]
            data = summary.dict()
            collection.replace_one(
                {"session_id": summary.session_id}, 
                data, 
                upsert=True
            )
            return True
        except PyMongoError as e:
            logger.error(f"儲存 ResearchSessionSummary 失敗: {e}")
            return False

    def get_events_by_symbol(self, symbol_key: str) -> List[Dict[str, Any]]:
        """按標的獲取研究歷史事件"""
        if not self._connected:
            return []
        try:
            collection = self.db["research_events"]
            cursor = collection.find({"symbol_key": symbol_key}).sort("timestamp", 1)
            return list(cursor)
        except PyMongoError:
            return []
