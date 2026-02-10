#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dexter Eval Models
定義評測結果與報告的數據結構
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class TestCaseResult(BaseModel):
    """
    單個測試案例的結果
    """
    test_id: str
    query: str
    symbol_key: str
    
    # 執行指標
    success: bool
    duration_ms: float
    total_steps: int
    tool_usage: List[str] # 實際使用的工具清單
    
    # 打分項 (0-100)
    tool_accuracy_score: float = 0.0 # 實際工具是否匹配預期
    reasoning_score: float = 0.0      # 推理深度/次數評分
    fact_coverage_score: float = 0.0  # (未來) 數據點覆蓋
    overall_score: float = 0.0
    
    # 錯誤詳情
    error: Optional[str] = None
    
    # 時間
    timestamp: datetime = Field(default_factory=datetime.now)

class EvalReport(BaseModel):
    """
    評測總整報告
    """
    report_id: str
    start_time: datetime
    end_time: datetime
    total_cases: int
    passed_cases: int
    failed_cases: int
    average_score: float
    
    results: List[TestCaseResult] = Field(default_factory=list)
    
    # 元數據 (Git Commit, etc)
    metadata: Dict[str, Any] = Field(default_factory=dict)
