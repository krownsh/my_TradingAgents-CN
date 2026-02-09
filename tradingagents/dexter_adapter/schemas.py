"""
Dexter Adapter Schemas

定義 Dexter 工具的輸入輸出結構，確保 market-aware 與資料品質追溯。
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class DexterToolInput(BaseModel):
    """
    Dexter 工具標準輸入格式
    
    使用 symbol_key 作為主要識別，確保市場與股票代碼明確。
    """
    symbol_key: str = Field(..., description="標準化 symbol key，格式：'US:AAPL' 或 'TW:2330'")
    
    @field_validator('symbol_key')
    @classmethod
    def validate_symbol_key(cls, v: str) -> str:
        """驗證 symbol_key 格式"""
        if ':' not in v:
            raise ValueError(
                f"symbol_key 必須包含市場前綴，格式：'US:AAPL' 或 'TW:2330'，收到：{v}"
            )
        market, symbol = v.split(':', 1)
        if market not in ['US', 'TW', 'CN']:
            raise ValueError(f"不支援的市場：{market}，僅支援 US, TW, CN")
        if not symbol:
            raise ValueError("symbol 不可為空")
        return v


class PriceInput(DexterToolInput):
    """價格查詢輸入"""
    start_date: Optional[str] = Field(None, description="開始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="結束日期 (YYYY-MM-DD)")
    timeframe: Optional[Literal["1m", "5m", "15m", "1h", "1d"]] = Field("1d", description="時間框架")


class NewsInput(DexterToolInput):
    """新聞查詢輸入"""
    limit: int = Field(10, description="返回數量", ge=1, le=100)
    start_date: Optional[str] = Field(None, description="開始日期 (YYYY-MM-DD)")


class FundamentalsInput(DexterToolInput):
    """財報查詢輸入"""
    period: Literal["annual", "quarterly"] = Field("annual", description="財報週期")
    limit: int = Field(5, description="返回筆數", ge=1, le=20)


class DexterToolOutput(BaseModel):
    """
    Dexter 工具標準輸出格式
    
    包含完整的資料品質與來源追溯資訊。
    """
    data: Any = Field(..., description="實際資料內容")
    quality: Literal["REALTIME", "EOD", "DELAYED", "MISSING"] = Field(
        ...,
        description="資料品質：REALTIME=即時, EOD=收盤, DELAYED=延遲, MISSING=缺失"
    )
    source_provider: str = Field(..., description="資料來源 provider，如 'polygon', 'efinance'")
    asof: datetime = Field(..., description="資料時間戳")
    source_urls: List[str] = Field(default_factory=list, description="可追溯的來源 URL")
    
    # 可選的額外資訊
    market: Optional[str] = Field(None, description="市場代碼 (US/TW/CN)")
    symbol: Optional[str] = Field(None, description="股票代碼")
    message: Optional[str] = Field(None, description="額外說明，如降級原因、警告訊息")


class ResearchStep(BaseModel):
    """研究計畫中的單一步驟"""
    step_id: str = Field(..., description="步驟唯一 ID")
    tool_name: str = Field(..., description="工具名稱，如 'market.bars'")
    args_schema: Dict[str, Any] = Field(..., description="工具參數")
    expected_output: str = Field(..., description="預期輸出說明")
    validation_rules: List[str] = Field(
        default_factory=list,
        description="驗證規則，如 ['price_range_valid', 'date_alignment']"
    )


class ResearchPlan(BaseModel):
    """
    Dexter Planner 生成的研究計畫
    
    結構化的研究步驟，方便 UI 顯示與執行追蹤。
    """
    objective: str = Field(..., description="研究目標")
    constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="約束條件，如 {market: 'TW', date_range: [...], quality: 'EOD'}"
    )
    steps: List[ResearchStep] = Field(..., description="研究步驟列表")
    
    # 元資料
    created_at: datetime = Field(default_factory=datetime.utcnow)
    symbol_key: Optional[str] = Field(None, description="主要研究標的")


class ToolResult(BaseModel):
    """單一工具執行結果"""
    step_id: str
    tool_name: str
    args: Dict[str, Any]
    output: DexterToolOutput
    duration_ms: int = Field(..., description="執行時間（毫秒）")
    success: bool = Field(True, description="是否成功")
    error: Optional[str] = Field(None, description="錯誤訊息")


class ValidationIssue(BaseModel):
    """驗證問題"""
    severity: Literal["error", "warning", "info"] = Field(..., description="嚴重程度")
    message: str = Field(..., description="問題說明")
    step_id: Optional[str] = Field(None, description="相關步驟 ID")
    rule: Optional[str] = Field(None, description="觸發的驗證規則")


class ValidationReport(BaseModel):
    """驗證報告"""
    passed: bool = Field(..., description="是否通過所有驗證")
    issues: List[ValidationIssue] = Field(default_factory=list, description="發現的問題")
    summary: str = Field(..., description="驗證摘要")
