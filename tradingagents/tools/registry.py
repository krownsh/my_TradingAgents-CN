#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具註冊表 (Tool Registry)
負責管理、封裝資料獲取功能，並提供給 Agent 作為 Tool Calling 使用
"""

import inspect
import logging
from typing import Dict, List, Any, Callable, Optional, Type
from pydantic import BaseModel, create_model

logger = logging.getLogger(__name__)

class ToolSpec(BaseModel):
    """工具定義規範"""
    name: str
    description: str
    parameters: Dict[str, Any]
    plugin: Optional[str] = None

class ToolRegistry:
    """工具註冊中心"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._specs: Dict[str, ToolSpec] = {}

    def register(self, name: str, description: str, plugin: Optional[str] = None):
        """工具註冊裝飾器"""
        def decorator(func: Callable):
            self._tools[name] = func
            # 獲取函數簽名並轉化為 JSON Schema
            sig = inspect.signature(func)
            parameters = self._generate_json_schema(sig)
            
            self._specs[name] = ToolSpec(
                name=name,
                description=description,
                parameters=parameters,
                plugin=plugin
            )
            return func
        return decorator

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """獲取所有工具的 JSON Schema (供 LLM 使用)"""
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters
                }
            }
            for spec in self._specs.values()
        ]

    def execute(self, name: str, **kwargs) -> Any:
        """執行工具"""
        if name not in self._tools:
            raise ValueError(f"工具 '{name}' 未註冊")
        
        logger.info(f"執行工具: {name}, 參數: {kwargs}")
        try:
            return self._tools[name](**kwargs)
        except Exception as e:
            logger.error(f"執行工具 '{name}' 失敗: {str(e)}")
            return f"Error: {str(e)}"

    def _generate_json_schema(self, sig: inspect.Signature) -> Dict[str, Any]:
        """從 Python 簽名生成 JSON Schema"""
        properties = {}
        required = []
        
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
                
            p_type = "string"
            if param.annotation == int:
                p_type = "integer"
            elif param.annotation == float:
                p_type = "number"
            elif param.annotation == bool:
                p_type = "boolean"
            elif param.annotation == list or param.annotation == List[str]:
                p_type = "array"
            
            properties[name] = {
                "type": p_type,
                "description": f"Parameter {name}"  # 這裡可以進一步優化，從 docstring 提取
            }
            
            if param.default == inspect.Parameter.empty:
                required.append(name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

# 全域單例
tool_registry = ToolRegistry()
