# -*- coding: utf-8 -*-
"""
安裝 Daily Analysis 模組所需的額外依賴

使用方式：
python install_daily_analysis_deps.py
"""
import subprocess
import sys

# Daily Analysis 額外需要的依賴（不在主 requirements.txt 中的）
DAILY_ANALYSIS_DEPS = [
    "efinance>=0.5.5",          # 東方財富數據源
    "FinMind>=1.5.0",            # 台灣市場數據源
    "tavily-python>=0.3.0",      # Tavily 搜索 API
    "google-search-results>=2.4.0",  # SerpAPI
    "google-generativeai>=0.8.0",    # Gemini API
    "lark-oapi>=1.0.0",          # 飛書 API
    "json-repair>=0.55.1",       # JSON 修復
    "markdown2>=2.4.0",          # Markdown 轉 HTML
    "fake-useragent>=1.4.0",     # 隨機 User-Agent
    "schedule>=1.2.0",           # 定時任務調度
    "tenacity>=8.2.0",           # 重試機制
    "newspaper3k>=0.2.8",        # 文章提取
    "lxml_html_clean",           # lxml 修復
    # Bot 平台（暫不使用，但保留安裝）
    "dingtalk-stream>=0.24.3",   # 釘釘 Stream SDK
    "discord.py>=2.0.0",         # Discord 機器人
]

def main():
    print("=" * 70)
    print("安裝 Daily Analysis 模組額外依賴")
    print("=" * 70)
    
    print(f"\n將安裝 {len(DAILY_ANALYSIS_DEPS)} 個套件...\n")
    
    for dep in DAILY_ANALYSIS_DEPS:
        print(f"📦 安裝: {dep}")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", dep
            ])
            print(f"✅ 成功: {dep}\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ 失敗: {dep}")
            print(f"   錯誤: {e}\n")
            
    print("=" * 70)
    print("✅ Daily Analysis 依賴安裝完成！")
    print("=" * 70)
    print("\n提示：如果安裝失敗，可以手動安裝：")
    print("pip install -r tradingagents/daily_analysis/requirements.txt")

if __name__ == "__main__":
    main()
