# -*- coding: utf-8 -*-
"""
自動調整 daily_analysis 模組的導入路徑
"""
import os
import re
from pathlib import Path

# 根目錄
ROOT_DIR = Path(r"d:\others\sideproject\stock analysis\my_TradingAgents-CN\tradingagents\daily_analysis")

# 導入路徑映射規則
IMPORT_MAPPINGS = [
    # src.* → tradingagents.daily_analysis.*
    (r'from src\.', 'from tradingagents.daily_analysis.'),
    (r'import src\.', 'import tradingagents.daily_analysis.'),
    
    # bot.* → tradingagents.daily_analysis.bot.*
    (r'from bot\.', 'from tradingagents.daily_analysis.bot.'),
    (r'import bot\.', 'import tradingagents.daily_analysis.bot.'),
    
    # data_provider → tradingagents.data_provider (共用)
    (r'from tradingagents.data_provider import', 'from tradingagents.data_provider import'),
    (r'import tradingagents.data_provider', 'import tradingagents.data_provider'),
]

def fix_imports_in_file(file_path: Path):
    """修正單個文件的導入路徑"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 應用所有映射規則
        for pattern, replacement in IMPORT_MAPPINGS:
            content = re.sub(pattern, replacement, content)
        
        # 如果有變更，寫回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 已修正: {file_path.relative_to(ROOT_DIR)}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"✗ 錯誤: {file_path} - {e}")
        return False

def main():
    """遍歷所有 Python 文件並修正導入"""
    print(f"開始掃描目錄: {ROOT_DIR}\n")
    
    fixed_count = 0
    total_count = 0
    
    for py_file in ROOT_DIR.rglob("*.py"):
        # 跳過 __pycache__
        if "__pycache__" in str(py_file):
            continue
        
        total_count += 1
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"\n完成! 共掃描 {total_count} 個文件，修正 {fixed_count} 個文件")

if __name__ == "__main__":
    main()
