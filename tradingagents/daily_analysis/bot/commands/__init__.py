# -*- coding: utf-8 -*-
"""
===================================
命令处理器模块
===================================

包含所有机器人命令的实现。
"""

from tradingagents.daily_analysis.bot.commands.base import BotCommand
from tradingagents.daily_analysis.bot.commands.help import HelpCommand
from tradingagents.daily_analysis.bot.commands.status import StatusCommand
from tradingagents.daily_analysis.bot.commands.analyze import AnalyzeCommand
from tradingagents.daily_analysis.bot.commands.market import MarketCommand
from tradingagents.daily_analysis.bot.commands.batch import BatchCommand

# 所有可用命令（用于自动注册）
ALL_COMMANDS = [
    HelpCommand,
    StatusCommand,
    AnalyzeCommand,
    MarketCommand,
    BatchCommand,
]

__all__ = [
    'BotCommand',
    'HelpCommand',
    'StatusCommand',
    'AnalyzeCommand',
    'MarketCommand',
    'BatchCommand',
    'ALL_COMMANDS',
]
