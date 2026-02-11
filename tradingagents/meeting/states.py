"""
會議室狀態機狀態定義
"""

from enum import Enum


class MeetingState(str, Enum):
    """會議狀態枚舉"""
    INIT = "INIT"                # 初始化
    PLAN = "PLAN"                # Dexter 計畫生成
    VALIDATE = "VALIDATE"        # 驗證計畫安全性與效率
    EXECUTE = "EXECUTE"          # 執行研究步驟
    DISCUSS = "DISCUSS"          # 專家討論
    SYNTHESIZE = "SYNTHESIZE"    # 總結報告
    FINISHED = "FINISHED"        # 會議結束
