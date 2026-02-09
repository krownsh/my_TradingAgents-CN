#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
會議室路由 (Meeting Router)
提供 REST 與 WebSocket 接口
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from app.services.meeting_service import meeting_service
from tradingagents.meeting.schemas import MeetingEvent

router = APIRouter()
logger = logging.getLogger("webapi.meeting")

@router.post("/meeting/start")
async def start_meeting(symbol_key: str, query: str):
    """
    發起同步會議 (返回最終報告)
    """
    try:
        report = await meeting_service.start_meeting(symbol_key, query)
        return report
    except Exception as e:
        logger.error(f"❌ 會議啟動失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/meeting")
async def websocket_meeting_endpoint(
    websocket: WebSocket,
    symbol_key: str = Query(...),
    query: str = Query(...)
):
    """
    WebSocket 會議室
    ws://localhost:8000/api/ws/meeting?symbol_key=US:AAPL&query=蘋果未來展望
    """
    await websocket.accept()
    logger.info(f"✅ [WS-Meeting] 新連接: symbol={symbol_key}")
    
    async def event_callback(event: MeetingEvent):
        try:
            await websocket.send_json(event.dict())
        except Exception as e:
            logger.error(f"❌ [WS-Meeting] 發送事件失敗: {e}")

    try:
        await meeting_service.start_meeting(symbol_key, query, callback=event_callback)
    except WebSocketDisconnect:
        logger.info(f"🔌 [WS-Meeting] 客戶端中斷連接: {symbol_key}")
    except Exception as e:
        logger.error(f"❌ [WS-Meeting] 會議執行出錯: {e}")
        await websocket.send_json({"event_type": "error", "payload": {"message": str(e)}})
    finally:
        await websocket.close()
