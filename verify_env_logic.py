import os
import sys

# 模擬從不同環境變數中讀取
def test_config_logic():
    print("Testing config logic...")
    
    # 測試 Gemini
    os.environ['GOOGLE_GEMINI_API_KEY'] = 'new_key'
    os.environ['GEMINI_API_KEY'] = 'old_key'
    
    gemini_key = os.getenv('GOOGLE_GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
    print(f"Gemini Key (should be new_key): {gemini_key}")
    assert gemini_key == 'new_key'
    
    # 測試 Tavily
    os.environ['TAVILY_API_KEY'] = 'single_key'
    tavily_key = os.getenv('TAVILY_API_KEY') or os.getenv('TAVILY_API_KEYS')
    print(f"Tavily Key (should be single_key): {tavily_key}")
    assert tavily_key == 'single_key'
    
    print("All tests passed!")

if __name__ == "__main__":
    test_config_logic()
