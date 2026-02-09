#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
會議室服務 (Meeting Service)
橋接 FastAPI 與 MeetingOrchestrator
"""

import logging
from typing import Dict, Any, Callable, Optional
from tradingagents.meeting.orchestrator import MeetingOrchestrator
from tradingagents.graph.trading_graph import create_llm_by_provider
from app.services.config_service import config_service

logger = logging.getLogger(__name__)

class MeetingService:
    """會議室後端服務"""
    
    def __init__(self):
        self.orchestrator = MeetingOrchestrator(self._llm_factory)

    def _llm_factory(self, role: str):
        """根據角色及系統配置創建 LLM"""
        # 這裡從數據庫獲取最新配置
        # 為了簡便，我們獲取 "default_llm" 或 "deep_analysis_model"
        # 實際應根據專家角色分配不同模型
        
        # 異步獲取配置在 factory 裡比較難處理，
        # 我們假設 service 會預先加載或使用同步方式 (或 run_async)
        import asyncio
        from tradingagents.utils.async_utils import run_async
        
        config = run_async(config_service.get_system_config())
        if not config:
            raise ValueError("系統配置中找不到有效的 LLM 配置")
            
        settings = config.system_settings
        # 預設使用 deep_analysis_model (如果存在)
        model_name = settings.get("deep_analysis_model") or config.default_llm
        
        # 找到對應的 LLMConfig
        llm_cfg = next((c for c in config.llm_configs if c.model_name == model_name), config.llm_configs[0])
        
        return create_llm_by_provider(
            provider=llm_cfg.provider.value,
            model=llm_cfg.model_name,
            backend_url=llm_cfg.api_base,
            temperature=llm_cfg.temperature,
            max_tokens=llm_cfg.max_tokens,
            timeout=llm_cfg.timeout or 180,
            api_key=llm_cfg.api_key
        )

    async def start_meeting(self, symbol_key: str, query: str, callback: Optional[Callable] = None):
        """發起會議"""
        logger.info(f"🚀 [MeetingService] 發起會議: {symbol_key} - {query}")
        return await self.orchestrator.run_meeting(symbol_key, query, callback)

# 單例
meeting_service = MeetingService()
