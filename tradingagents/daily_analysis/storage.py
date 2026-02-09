# -*- coding: utf-8 -*-
"""
===================================
A股自選股智能分析系統 - 存儲層
===================================

職責：
1. 管理 SQLite 資料庫連接（單例模式）
2. 定義 ORM 數據模型
3. 提供數據存取接口
4. 實現智能更新邏輯（斷點續傳）
"""

import atexit
import hashlib
import json
import logging
import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    Date,
    DateTime,
    Integer,
    Index,
    UniqueConstraint,
    Text,
    select,
    and_,
    desc,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session,
)
from sqlalchemy.exc import IntegrityError

from tradingagents.daily_analysis.config import get_config

logger = logging.getLogger(__name__)

# SQLAlchemy ORM 基類
Base = declarative_base()

if TYPE_CHECKING:
    from tradingagents.daily_analysis.search_service import SearchResponse


# === 數據模型定義 ===

class StockDaily(Base):
    """
    股票日線數據模型
    
    存儲每日行情數據和計算的技術指標
    支持多股票、多日期的唯一約束
    """
    __tablename__ = 'stock_daily'
    
    # 主鍵
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 股票代碼（如 600519, 000001）
    code = Column(String(10), nullable=False, index=True)
    
    # 交易日期
    date = Column(Date, nullable=False, index=True)
    
    # OHLC 數據
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    
    # 成交數據
    volume = Column(Float)  # 成交量（股）
    amount = Column(Float)  # 成交額（元）
    pct_chg = Column(Float)  # 漲跌幅（%）
    
    # 技術指標
    ma5 = Column(Float)
    ma10 = Column(Float)
    ma20 = Column(Float)
    volume_ratio = Column(Float)  # 量比
    
    # 台灣股票特有籌碼數據
    foreign_buy = Column(Float)    # 外資買賣超
    it_buy = Column(Float)         # 投信買賣超
    dealers_buy = Column(Float)    # 自營商買賣超
    margin_buy = Column(Float)     # 融資買賣
    short_buy = Column(Float)      # 融券買賣
    revenue_yoy = Column(Float)    # 營收年增率 (%)
    
    # 數據來源
    data_source = Column(String(50))  # 記錄數據來源（如 AkshareFetcher）
    
    # 更新時間
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 唯一約束：同一股票同一日期只能有一條數據
    __table_args__ = (
        UniqueConstraint('code', 'date', name='uix_code_date'),
        Index('ix_code_date', 'code', 'date'),
    )
    
    def __repr__(self):
        return f"<StockDaily(code={self.code}, date={self.date}, close={self.close})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'code': self.code,
            'date': self.date,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'amount': self.amount,
            'pct_chg': self.pct_chg,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'volume_ratio': self.volume_ratio,
            'foreign_buy': self.foreign_buy,
            'it_buy': self.it_buy,
            'dealers_buy': self.dealers_buy,
            'margin_buy': self.margin_buy,
            'short_buy': self.short_buy,
            'revenue_yoy': self.revenue_yoy,
            'data_source': self.data_source,
        }


class NewsIntel(Base):
    """
    新聞情報數據模型

    存儲搜尋到的新聞情報條目，用於後續分析與查詢
    """
    __tablename__ = 'news_intel'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 關聯用戶查詢操作
    query_id = Column(String(64), index=True)

    # 股票信息
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50))

    # 搜尋上下文
    dimension = Column(String(32), index=True)  # latest_news / risk_check / earnings / market_analysis / industry
    query = Column(String(255))
    provider = Column(String(32), index=True)

    # 新聞內容
    title = Column(String(300), nullable=False)
    snippet = Column(Text)
    url = Column(String(1000), nullable=False)
    source = Column(String(100))
    published_date = Column(DateTime, index=True)

    # 入庫時間
    fetched_at = Column(DateTime, default=datetime.now, index=True)
    query_source = Column(String(32), index=True)  # bot/web/cli/system
    requester_platform = Column(String(20))
    requester_user_id = Column(String(64))
    requester_user_name = Column(String(64))
    requester_chat_id = Column(String(64))
    requester_message_id = Column(String(64))
    requester_query = Column(String(255))

    __table_args__ = (
        UniqueConstraint('url', name='uix_news_url'),
        Index('ix_news_code_pub', 'code', 'published_date'),
    )

    def __repr__(self) -> str:
        return f"<NewsIntel(code={self.code}, title={self.title[:20]}...)>"


class AnalysisHistory(Base):
    """
    分析結果歷史記錄模型

    保存每次分析結果，支持按 query_id/股票代碼檢索
    """
    __tablename__ = 'analysis_history'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 關聯查詢鏈路
    query_id = Column(String(64), index=True)

    # 股票信息
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50))
    report_type = Column(String(16), index=True)

    # 核心結論
    sentiment_score = Column(Integer)
    operation_advice = Column(String(20))
    trend_prediction = Column(String(50))
    analysis_summary = Column(Text)

    # 詳細數據
    raw_result = Column(Text)
    news_content = Column(Text)
    context_snapshot = Column(Text)

    # 狙擊點位（用於回測）
    ideal_buy = Column(Float)
    secondary_buy = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)

    created_at = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index('ix_analysis_code_time', 'code', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'id': self.id,
            'query_id': self.query_id,
            'code': self.code,
            'name': self.name,
            'report_type': self.report_type,
            'sentiment_score': self.sentiment_score,
            'operation_advice': self.operation_advice,
            'trend_prediction': self.trend_prediction,
            'analysis_summary': self.analysis_summary,
            'raw_result': self.raw_result,
            'news_content': self.news_content,
            'context_snapshot': self.context_snapshot,
            'ideal_buy': self.ideal_buy,
            'secondary_buy': self.secondary_buy,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DatabaseManager:
    """
    資料庫管理器 - 單例模式
    
    職責：
    1. 管理資料庫連接池
    2. 提供 Session 上下文管理
    3. 封裝數據存取操作
    """
    
    _instance: Optional['DatabaseManager'] = None
    
    def __new__(cls, *args, **kwargs):
        """單例模式實現"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化資料庫管理器
        
        Args:
            db_url: 資料庫連接 URL（可選，默認從配置讀取）
        """
        if self._initialized:
            return
        
        if db_url is None:
            config = get_config()
            db_url = config.get_db_url()
        
        # 建立資料庫引擎
        self._engine = create_engine(
            db_url,
            echo=False,  # 設為 True 可查看 SQL 語句
            pool_pre_ping=True,  # 連接健康檢查
        )
        
        # 建立 Session 工廠
        self._SessionLocal = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
        )
        
        # 建立所有表
        Base.metadata.create_all(self._engine)

        self._initialized = True
        logger.info(f"資料庫初始化完成: {db_url}")

        # 註冊退出鉤子，確保程序退出時關閉資料庫連接
        atexit.register(DatabaseManager._cleanup_engine, self._engine)
    
    @classmethod
    def get_instance(cls) -> 'DatabaseManager':
        """獲取單例實例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置單例（用於測試）"""
        if cls._instance is not None:
            cls._instance._engine.dispose()
            cls._instance = None

    @classmethod
    def _cleanup_engine(cls, engine) -> None:
        """
        清理資料庫引擎（atexit 鉤子）

        確保程序退出時關閉所有資料庫連接，避免 ResourceWarning

        Args:
            engine: SQLAlchemy 引擎對象
        """
        try:
            if engine is not None:
                engine.dispose()
                logger.debug("資料庫引擎已清理")
        except Exception as e:
            logger.warning(f"清理資料庫引擎時出錯: {e}")
    
    def get_session(self) -> Session:
        """
        獲取資料庫 Session
        
        使用示例:
            with db.get_session() as session:
                # 執行查詢
                session.commit()  # 如果需要
        """
        session = self._SessionLocal()
        try:
            return session
        except Exception:
            session.close()
            raise
    
    def has_today_data(self, code: str, target_date: Optional[date] = None) -> bool:
        """
        檢查是否已有指定日期的数据
        
        用於斷點續傳邏輯：如果已有數據則跳過網絡請求
        
        Args:
            code: 股票代碼
            target_date: 目標日期（默認今天）
            
        Returns:
            是否存在數據
        """
        if target_date is None:
            target_date = date.today()
        
        with self.get_session() as session:
            result = session.execute(
                select(StockDaily).where(
                    and_(
                        StockDaily.code == code,
                        StockDaily.date == target_date
                    )
                )
            ).scalar_one_or_none()
            
            return result is not None
    
    def get_latest_data(
        self, 
        code: str, 
        days: int = 2
    ) -> List[StockDaily]:
        """
        獲取最近 N 天的数据
        
        用於計算"相比昨日"的變化
        
        Args:
            code: 股票代碼
            days: 獲取天數
            
        Returns:
            StockDaily 對象列表（按日期降序）
        """
        with self.get_session() as session:
            results = session.execute(
                select(StockDaily)
                .where(StockDaily.code == code)
                .order_by(desc(StockDaily.date))
                .limit(days)
            ).scalars().all()
            
            return list(results)

    def save_news_intel(
        self,
        code: str,
        name: str,
        dimension: str,
        query: str,
        response: 'SearchResponse',
        query_context: Optional[Dict[str, str]] = None
    ) -> int:
        """
        保存新聞情報到資料庫

        去重策略：
        - 優先按 URL 去重（唯一約束）
        - URL 缺失時按 title + source + published_date 進行軟去重

        關聯策略：
        - query_context 記錄用戶查詢信息（平台、用戶、會話、原始指令等）
        """
        if not response or not response.results:
            return 0

        saved_count = 0

        with self.get_session() as session:
            try:
                for item in response.results:
                    title = (item.title or '').strip()
                    url = (item.url or '').strip()
                    source = (item.source or '').strip()
                    snippet = (item.snippet or '').strip()
                    published_date = self._parse_published_date(item.published_date)

                    if not title and not url:
                        continue

                    url_key = url or self._build_fallback_url_key(
                        code=code,
                        title=title,
                        source=source,
                        published_date=published_date
                    )

                    # 優先按 URL 或兜底鍵去重
                    existing = session.execute(
                        select(NewsIntel).where(NewsIntel.url == url_key)
                    ).scalar_one_or_none()

                    if existing:
                        existing.name = name or existing.name
                        existing.dimension = dimension or existing.dimension
                        existing.query = query or existing.query
                        existing.provider = response.provider or existing.provider
                        existing.snippet = snippet or existing.snippet
                        existing.source = source or existing.source
                        existing.published_date = published_date or existing.published_date
                        existing.fetched_at = datetime.now()

                        if query_context:
                            existing.query_id = query_context.get("query_id") or existing.query_id
                            existing.query_source = query_context.get("query_source") or existing.query_source
                            existing.requester_platform = query_context.get("requester_platform") or existing.requester_platform
                            existing.requester_user_id = query_context.get("requester_user_id") or existing.requester_user_id
                            existing.requester_user_name = query_context.get("requester_user_name") or existing.requester_user_name
                            existing.requester_chat_id = query_context.get("requester_chat_id") or existing.requester_chat_id
                            existing.requester_message_id = query_context.get("requester_message_id") or existing.requester_message_id
                            existing.requester_query = query_context.get("requester_query") or existing.requester_query
                    else:
                        try:
                            with session.begin_nested():
                                record = NewsIntel(
                                    code=code,
                                    name=name,
                                    dimension=dimension,
                                    query=query,
                                    provider=response.provider,
                                    title=title,
                                    snippet=snippet,
                                    url=url_key,
                                    source=source,
                                    published_date=published_date,
                                    fetched_at=datetime.now(),
                                    query_id=(query_context or {}).get("query_id"),
                                    query_source=(query_context or {}).get("query_source"),
                                    requester_platform=(query_context or {}).get("requester_platform"),
                                    requester_user_id=(query_context or {}).get("requester_user_id"),
                                    requester_user_name=(query_context or {}).get("requester_user_name"),
                                    requester_chat_id=(query_context or {}).get("requester_chat_id"),
                                    requester_message_id=(query_context or {}).get("requester_message_id"),
                                    requester_query=(query_context or {}).get("requester_query"),
                                )
                                session.add(record)
                                session.flush()
                            saved_count += 1
                        except IntegrityError:
                            # 單條 URL 唯一約束衝突（如併發插入），僅跳過本條，保留本批其餘成功項
                            logger.debug("新聞情報重複（已跳過）: %s %s", code, url_key)

                session.commit()
                logger.info(f"保存新聞情報成功: {code}, 新增 {saved_count} 條")

            except Exception as e:
                session.rollback()
                logger.error(f"保存新聞情報失敗: {e}")
                raise

        return saved_count

    def get_recent_news(self, code: str, days: int = 7, limit: int = 20) -> List[NewsIntel]:
        """
        獲取指定股票最近 N 天的新聞情報
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        with self.get_session() as session:
            results = session.execute(
                select(NewsIntel)
                .where(
                    and_(
                        NewsIntel.code == code,
                        NewsIntel.fetched_at >= cutoff_date
                    )
                )
                .order_by(desc(NewsIntel.fetched_at))
                .limit(limit)
            ).scalars().all()

            return list(results)

    def save_analysis_history(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str],
        context_snapshot: Optional[Dict[str, Any]] = None,
        save_snapshot: bool = True
    ) -> int:
        """
        保存分析結果歷史記錄
        """
        if result is None:
            return 0

        sniper_points = self._extract_sniper_points(result)
        raw_result = self._build_raw_result(result)
        context_text = None
        if save_snapshot and context_snapshot is not None:
            context_text = self._safe_json_dumps(context_snapshot)

        record = AnalysisHistory(
            query_id=query_id,
            code=result.code,
            name=result.name,
            report_type=report_type,
            sentiment_score=result.sentiment_score,
            operation_advice=result.operation_advice,
            trend_prediction=result.trend_prediction,
            analysis_summary=result.analysis_summary,
            raw_result=self._safe_json_dumps(raw_result),
            news_content=news_content,
            context_snapshot=context_text,
            ideal_buy=sniper_points.get("ideal_buy"),
            secondary_buy=sniper_points.get("secondary_buy"),
            stop_loss=sniper_points.get("stop_loss"),
            take_profit=sniper_points.get("take_profit"),
            created_at=datetime.now(),
        )

        with self.get_session() as session:
            try:
                session.add(record)
                session.commit()
                return 1
            except Exception as e:
                session.rollback()
                logger.error(f"保存分析歷史失敗: {e}")
                return 0

    def get_analysis_history(
        self,
        code: Optional[str] = None,
        query_id: Optional[str] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[AnalysisHistory]:
        """
        查詢分析歷史記錄
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        with self.get_session() as session:
            conditions = [AnalysisHistory.created_at >= cutoff_date]
            if code:
                conditions.append(AnalysisHistory.code == code)
            if query_id:
                conditions.append(AnalysisHistory.query_id == query_id)

            results = session.execute(
                select(AnalysisHistory)
                .where(and_(*conditions))
                .order_by(desc(AnalysisHistory.created_at))
                .limit(limit)
            ).scalars().all()

            return list(results)
    
    def get_data_range(
        self, 
        code: str, 
        start_date: date, 
        end_date: date
    ) -> List[StockDaily]:
        """
        獲取指定日期範圍的数据
        
        Args:
            code: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            StockDaily 對象列表
        """
        with self.get_session() as session:
            results = session.execute(
                select(StockDaily)
                .where(
                    and_(
                        StockDaily.code == code,
                        StockDaily.date >= start_date,
                        StockDaily.date <= end_date
                    )
                )
                .order_by(StockDaily.date)
            ).scalars().all()
            
            return list(results)
    
    def save_daily_data(
        self, 
        df: pd.DataFrame, 
        code: str,
        data_source: str = "Unknown"
    ) -> int:
        """
        保存日線數據到資料庫
        
        策略：
        - 使用 UPSERT 邏輯（存在則更新，不存在則插入）
        - 跳過已存在的數據，避免重複
        
        Args:
            df: 包含日線數據的 DataFrame
            code: 股票代碼
            data_source: 數據來源名稱
            
        Returns:
            新增/更新的記錄數
        """
        if df is None or df.empty:
            logger.warning(f"保存數據為空，跳過 {code}")
            return 0
        
        saved_count = 0
        
        with self.get_session() as session:
            try:
                for _, row in df.iterrows():
                    # 解析日期
                    row_date = row.get('date')
                    if isinstance(row_date, str):
                        row_date = datetime.strptime(row_date, '%Y-%m-%d').date()
                    elif isinstance(row_date, datetime):
                        row_date = row_date.date()
                    elif isinstance(row_date, pd.Timestamp):
                        row_date = row_date.date()
                    
                    # 檢查是否已存在
                    existing = session.execute(
                        select(StockDaily).where(
                            and_(
                                StockDaily.code == code,
                                StockDaily.date == row_date
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if existing:
                        # 更新現有記錄
                        existing.open = row.get('open')
                        existing.high = row.get('high')
                        existing.low = row.get('low')
                        existing.close = row.get('close')
                        existing.volume = row.get('volume')
                        existing.amount = row.get('amount')
                        existing.pct_chg = row.get('pct_chg')
                        existing.ma5 = row.get('ma5')
                        existing.ma10 = row.get('ma10')
                        existing.ma20 = row.get('ma20')
                        existing.volume_ratio = row.get('volume_ratio')
                        existing.foreign_buy = row.get('foreign_buy')
                        existing.it_buy = row.get('it_buy')
                        existing.dealers_buy = row.get('dealers_buy')
                        existing.margin_buy = row.get('margin_buy')
                        existing.short_buy = row.get('short_buy')
                        existing.revenue_yoy = row.get('revenue_yoy')
                        existing.data_source = data_source
                        existing.updated_at = datetime.now()
                    else:
                        # 建立新記錄
                        record = StockDaily(
                            code=code,
                            date=row_date,
                            open=row.get('open'),
                            high=row.get('high'),
                            low=row.get('low'),
                            close=row.get('close'),
                            volume=row.get('volume'),
                            amount=row.get('amount'),
                            pct_chg=row.get('pct_chg'),
                            ma5=row.get('ma5'),
                            ma10=row.get('ma10'),
                            ma20=row.get('ma20'),
                            volume_ratio=row.get('volume_ratio'),
                            foreign_buy=row.get('foreign_buy'),
                            it_buy=row.get('it_buy'),
                            dealers_buy=row.get('dealers_buy'),
                            margin_buy=row.get('margin_buy'),
                            short_buy=row.get('short_buy'),
                            revenue_yoy=row.get('revenue_yoy'),
                            data_source=data_source,
                        )
                        session.add(record)
                        saved_count += 1
                
                session.commit()
                logger.info(f"保存 {code} 數據成功，新增 {saved_count} 條")
                
            except Exception as e:
                session.rollback()
                logger.error(f"保存 {code} 數據失敗: {e}")
                raise
        
        return saved_count
    
    def get_analysis_context(
        self, 
        code: str,
        target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        獲取分析所需的上下文數據
        
        返回今日數據 + 昨日數據的對比信息
        
        Args:
            code: 股票代碼
            target_date: 目標日期（默認今天）
            
        Returns:
            包含今日數據、昨日對比等信息的字典
        """
        if target_date is None:
            target_date = date.today()
        
        # 獲取最近2天數據
        recent_data = self.get_latest_data(code, days=2)
        
        if not recent_data:
            logger.warning(f"未找到 {code} 的數據")
            return None
        
        today_data = recent_data[0]
        yesterday_data = recent_data[1] if len(recent_data) > 1 else None
        
        context = {
            'code': code,
            'date': today_data.date.isoformat(),
            'today': today_data.to_dict(),
        }
        
        if yesterday_data:
            context['yesterday'] = yesterday_data.to_dict()
            
            # 計算相比昨日的變化
            if yesterday_data.volume and yesterday_data.volume > 0:
                context['volume_change_ratio'] = round(
                    today_data.volume / yesterday_data.volume, 2
                )
            
            if yesterday_data.close and yesterday_data.close > 0:
                context['price_change_ratio'] = round(
                    (today_data.close - yesterday_data.close) / yesterday_data.close * 100, 2
                )
            
            # 均線形態判斷
            context['ma_status'] = self._analyze_ma_status(today_data)
        
        return context
    
    def _analyze_ma_status(self, data: StockDaily) -> str:
        """
        分析均線形態
        
        判斷條件：
        - 多頭排列：close > ma5 > ma10 > ma20
        - 空頭排列：close < ma5 < ma10 < ma20
        - 震盪整理：其他情況
        """
        close = data.close or 0
        ma5 = data.ma5 or 0
        ma10 = data.ma10 or 0
        ma20 = data.ma20 or 0
        
        if close > ma5 > ma10 > ma20 > 0:
            return "多頭排列 📈"
        elif close < ma5 < ma10 < ma20 and ma20 > 0:
            return "空頭排列 📉"
        elif close > ma5 and ma5 > ma10:
            return "短期向好 🔼"
        elif close < ma5 and ma5 < ma10:
            return "短期走弱 🔽"
        else:
            return "震盪整理 ↔️"

    @staticmethod
    def _parse_published_date(value: Optional[str]) -> Optional[datetime]:
        """
        解析發布時間字符串（失敗返回 None）
        """
        if not value:
            return None

        if isinstance(value, datetime):
            return value

        text = str(value).strip()
        if not text:
            return None

        # 優先嘗試 ISO 格式
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass

        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d",
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def _safe_json_dumps(data: Any) -> str:
        """
        安全序列化為 JSON 字符串
        """
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception:
            return json.dumps(str(data), ensure_ascii=False)

    @staticmethod
    def _build_raw_result(result: Any) -> Dict[str, Any]:
        """
        生成完整分析結果字典
        """
        data = result.to_dict() if hasattr(result, "to_dict") else {}
        data.update({
            'data_sources': getattr(result, 'data_sources', ''),
            'raw_response': getattr(result, 'raw_response', None),
        })
        return data

    @staticmethod
    def _parse_sniper_value(value: Any) -> Optional[float]:
        """
        解析狙擊點位數值
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).replace(',', '').strip()
        if not text:
            return None

        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group())
        except ValueError:
            return None

    def _extract_sniper_points(self, result: Any) -> Dict[str, Optional[float]]:
        """
        抽取狙擊點位數據
        """
        raw_points = {}
        if hasattr(result, "get_sniper_points"):
            raw_points = result.get_sniper_points() or {}

        return {
            "ideal_buy": self._parse_sniper_value(raw_points.get("ideal_buy")),
            "secondary_buy": self._parse_sniper_value(raw_points.get("secondary_buy")),
            "stop_loss": self._parse_sniper_value(raw_points.get("stop_loss")),
            "take_profit": self._parse_sniper_value(raw_points.get("take_profit")),
        }

    @staticmethod
    def _build_fallback_url_key(
        code: str,
        title: str,
        source: str,
        published_date: Optional[datetime]
    ) -> str:
        """
        生成無 URL 時的去重鍵（確保穩定且較短）
        """
        date_str = published_date.isoformat() if published_date else ""
        raw_key = f"{code}|{title}|{source}|{date_str}"
        digest = hashlib.md5(raw_key.encode("utf-8")).hexdigest()
        return f"no-url:{code}:{digest}"


# 便捷函數
def get_db() -> DatabaseManager:
    """獲取資料庫管理器實例的快捷方式"""
    return DatabaseManager.get_instance()


if __name__ == "__main__":
    # 測試代碼
    logging.basicConfig(level=logging.DEBUG)
    
    db = get_db()
    
    print("=== 資料庫測試 ===")
    print(f"資料庫初始化成功")
    
    # 測試檢查今日數據
    has_data = db.has_today_data('600519')
    print(f"茅台今日是否有數據: {has_data}")
    
    # 測試保存數據
    test_df = pd.DataFrame({
        'date': [date.today()],
        'open': [1800.0],
        'high': [1850.0],
        'low': [1780.0],
        'close': [1820.0],
        'volume': [10000000],
        'amount': [18200000000],
        'pct_chg': [1.5],
        'ma5': [1810.0],
        'ma10': [1800.0],
        'ma20': [1790.0],
        'volume_ratio': [1.2],
    })
    
    saved = db.save_daily_data(test_df, '600519', 'TestSource')
    print(f"保存測試數據: {saved} 條")
    
    # 測試獲取上下文
    context = db.get_analysis_context('600519')
    print(f"分析上下文: {context}")
