# -*- coding: utf-8 -*-
"""
Daily Analysis API 完整測試腳本

測試所有 5 個 API endpoints 的功能
"""
import asyncio
import httpx
import json
from typing import Dict, Any

# API Base URL
API_BASE = "http://localhost:8000"

class DailyAnalysisAPITester:
    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url
        self.client = None
        self.test_results = []
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_test(self, name: str, passed: bool, message: str = "", data: Any = None):
        """記錄測試結果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            "name": name,
            "passed": passed,
            "message": message,
            "data": data
        })
        print(f"\n{status} - {name}")
        if message:
            print(f"  📝 {message}")
        if data and not passed:
            print(f"  🐛 錯誤詳情: {data}")
    
    async def test_1_health_check(self):
        """測試 1: 健康檢查 GET /api/daily/health"""
        print("\n" + "=" * 70)
        print("測試 1: 健康檢查")
        print("=" * 70)
        
        try:
            response = await self.client.get(f"{self.base_url}/api/daily/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("status") == "healthy":
                    self.log_test(
                        "健康檢查",
                        True,
                        f"系統狀態: {data.get('status')}, 組件: {data.get('components')}"
                    )
                else:
                    self.log_test(
                        "健康檢查",
                        False,
                        "返回成功但狀態異常",
                        data
                    )
            else:
                self.log_test(
                    "健康檢查",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
        except Exception as e:
            self.log_test("健康檢查", False, f"連接失敗", str(e))
    
    async def test_2_get_config(self):
        """測試 2: 獲取配置 GET /api/daily/config"""
        print("\n" + "=" * 70)
        print("測試 2: 獲取系統配置")
        print("=" * 70)
        
        try:
            response = await self.client.get(f"{self.base_url}/api/daily/config")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    config = data.get("config", {})
                    print(f"\n📊 配置詳情:")
                    print(f"  - 自選股數量: {len(config.get('stock_list', []))}")
                    print(f"  - 最大併發: {config.get('max_workers')}")
                    print(f"  - 即時行情: {config.get('enable_realtime_quote')}")
                    print(f"  - 籌碼分佈: {config.get('enable_chip_distribution')}")
                    print(f"  - 報告類型: {config.get('report_type')}")
                    
                    channels = config.get('notification_channels', {})
                    active_channels = [k for k, v in channels.items() if v]
                    print(f"  - 推送渠道: {', '.join(active_channels) if active_channels else '無'}")
                    
                    self.log_test(
                        "獲取配置",
                        True,
                        f"成功獲取配置，{len(config.get('stock_list', []))} 隻自選股"
                    )
                else:
                    self.log_test("獲取配置", False, "success 為 false", data)
            else:
                self.log_test("獲取配置", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_test("獲取配置", False, "請求失敗", str(e))
    
    async def test_3_analyze_stocks_dry_run(self):
        """測試 3: 股票分析（僅獲取數據，不進行 AI 分析）"""
        print("\n" + "=" * 70)
        print("測試 3: 股票分析 - Dry Run 模式（僅數據獲取）")
        print("=" * 70)
        
        try:
            # 測試單隻股票，dry_run 模式（不需要 AI）
            payload = {
                "stock_codes": ["600519"],  # 貴州茅台
                "full_report": False,
                "send_notification": False,
                "dry_run": True  # 僅獲取數據，不進行 AI 分析
            }
            
            print(f"\n📤 請求 Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            
            response = await self.client.post(
                f"{self.base_url}/api/daily/analyze",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    results = data.get("results", [])
                    print(f"\n✅ 成功獲取 {len(results)} 隻股票的數據")
                    
                    for result in results:
                        print(f"\n  股票: {result.get('name')} ({result.get('code')})")
                        print(f"  數據獲取: 成功")
                    
                    self.log_test(
                        "股票分析 (Dry Run)",
                        True,
                        f"成功獲取 {len(results)} 隻股票數據"
                    )
                else:
                    self.log_test("股票分析 (Dry Run)", False, "返回 success=false", data)
            else:
                self.log_test(
                    "股票分析 (Dry Run)",
                    False,
                    f"HTTP {response.status_code}",
                    response.text
                )
        except Exception as e:
            self.log_test("股票分析 (Dry Run)", False, "請求失敗", str(e))
    
    async def test_4_analyze_stocks_with_ai(self):
        """測試 4: 股票分析（完整 AI 分析，需要 API Key）"""
        print("\n" + "=" * 70)
        print("測試 4: 股票分析 - 完整 AI 分析（需要 Gemini/OpenAI API Key）")
        print("=" * 70)
        
        try:
            payload = {
                "stock_codes": ["600519"],  # 貴州茅台
                "full_report": False,
                "send_notification": False,
                "dry_run": False  # 進行完整 AI 分析
            }
            
            print(f"\n📤 請求 Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            print("⚠️  此測試需要配置 DAILY_GEMINI_API_KEY 或 GEMINI_API_KEY")
            
            response = await self.client.post(
                f"{self.base_url}/api/daily/analyze",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    results = data.get("results", [])
                    print(f"\n✅ 成功分析 {len(results)} 隻股票")
                    
                    for result in results:
                        print(f"\n  📈 股票: {result.get('name')} ({result.get('code')})")
                        print(f"  操作建議: {result.get('operation_advice', 'N/A')}")
                        print(f"  情緒評分: {result.get('sentiment_score', 'N/A')}")
                        if result.get('buy_price'):
                            print(f"  買入價: {result.get('buy_price')}")
                            print(f"  止損價: {result.get('stop_loss')}")
                            print(f"  目標價: {result.get('target_price')}")
                    
                    self.log_test(
                        "股票分析 (AI)",
                        True,
                        f"成功分析 {len(results)} 隻股票"
                    )
                else:
                    self.log_test("股票分析 (AI)", False, "返回 success=false", data)
            else:
                error_text = response.text
                if "API key" in error_text or "GEMINI" in error_text:
                    self.log_test(
                        "股票分析 (AI)",
                        False,
                        "⚠️ 缺少 API Key，請在 .env 中配置 DAILY_GEMINI_API_KEY",
                        error_text
                    )
                else:
                    self.log_test(
                        "股票分析 (AI)",
                        False,
                        f"HTTP {response.status_code}",
                        error_text
                    )
        except Exception as e:
            self.log_test("股票分析 (AI)", False, "請求失敗", str(e))
    
    async def test_5_get_history(self):
        """測試 5: 獲取分析歷史"""
        print("\n" + "=" * 70)
        print("測試 5: 獲取分析歷史")
        print("=" * 70)
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/daily/history?limit=10"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    history = data.get("history", [])
                    print(f"\n📚 歷史記錄數量: {len(history)}")
                    
                    if history:
                        print("\n最近 3 筆記錄:")
                        for item in history[:3]:
                            print(f"  - {item.get('stock_name')} ({item.get('stock_code')})")
                            print(f"    操作: {item.get('operation_advice')}")
                            print(f"    時間: {item.get('created_at')}")
                    
                    self.log_test(
                        "獲取歷史",
                        True,
                        f"成功獲取 {len(history)} 筆歷史記錄"
                    )
                else:
                    self.log_test("獲取歷史", False, "返回 success=false", data)
            else:
                self.log_test("獲取歷史", False, f"HTTP {response.status_code}", response.text)
        except Exception as e:
            self.log_test("獲取歷史", False, "請求失敗", str(e))
    
    async def test_6_market_review(self):
        """測試 6: 大盤複盤（需要 AI API）"""
        print("\n" + "=" * 70)
        print("測試 6: 大盤複盤（需要 Gemini/OpenAI API Key）")
        print("=" * 70)
        
        try:
            payload = {
                "send_notification": False
            }
            
            print(f"\n📤 請求 Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            print("⚠️  此測試需要配置 DAILY_GEMINI_API_KEY 或 GEMINI_API_KEY")
            print("⏱️  大盤複盤可能需要 30-60 秒，請耐心等待...")
            
            response = await self.client.post(
                f"{self.base_url}/api/daily/market-review",
                json=payload,
                timeout=120.0  # 延長超時時間
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    report = data.get("report", "")
                    print(f"\n✅ 大盤複盤完成")
                    print(f"  報告長度: {len(report)} 字符")
                    if report:
                        print(f"\n  報告預覽:")
                        print(f"  {report[:200]}...")
                    
                    self.log_test(
                        "大盤複盤",
                        True,
                        f"成功生成複盤報告（{len(report)} 字符）"
                    )
                else:
                    self.log_test("大盤複盤", False, "返回 success=false", data)
            else:
                error_text = response.text
                if "API key" in error_text or "GEMINI" in error_text:
                    self.log_test(
                        "大盤複盤",
                        False,
                        "⚠️ 缺少 API Key，請在 .env 中配置 DAILY_GEMINI_API_KEY",
                        error_text
                    )
                else:
                    self.log_test(
                        "大盤複盤",
                        False,
                        f"HTTP {response.status_code}",
                        error_text
                    )
        except httpx.TimeoutException:
            self.log_test("大盤複盤", False, "請求超時（>120秒）", "可能需要更長時間")
        except Exception as e:
            self.log_test("大盤複盤", False, "請求失敗", str(e))
    
    def print_summary(self):
        """打印測試摘要"""
        print("\n" + "=" * 70)
        print("📊 測試摘要")
        print("=" * 70)
        
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        
        print(f"\n總計: {passed}/{total} 通過")
        print(f"通過率: {passed/total*100:.1f}%\n")
        
        for result in self.test_results:
            status = "✅" if result["passed"] else "❌"
            print(f"{status} {result['name']}")
            if result["message"]:
                print(f"   {result['message']}")
        
        print("\n" + "=" * 70)
        
        if passed == total:
            print("🎉 所有測試通過！Daily Analysis API 運作正常")
        else:
            print(f"⚠️  {total - passed} 個測試失敗，請檢查配置和服務狀態")
            print("\n💡 常見問題排查：")
            print("1. 確認後端服務已啟動（python -m uvicorn app.main:app）")
            print("2. 檢查 .env 文件中的 API Key 配置")
            print("3. 確認所有依賴已安裝（pip install -e .）")
        
        print("=" * 70)


async def main():
    """執行所有測試"""
    print("\n")
    print("🧪 Daily Analysis API 完整測試")
    print("=" * 70)
    print("測試目標: http://localhost:8000/api/daily/*")
    print("=" * 70)
    
    async with DailyAnalysisAPITester() as tester:
        # 測試 1: 健康檢查（不需要 API Key）
        await tester.test_1_health_check()
        
        # 測試 2: 獲取配置（不需要 API Key）
        await tester.test_2_get_config()
        
        # 測試 3: 股票分析 Dry Run（不需要 API Key）
        await tester.test_3_analyze_stocks_dry_run()
        
        # 測試 4: 股票分析 AI（需要 API Key）
        await tester.test_4_analyze_stocks_with_ai()
        
        # 測試 5: 獲取歷史（不需要 API Key）
        await tester.test_5_get_history()
        
        # 測試 6: 大盤複盤（需要 API Key，較慢）
        # await tester.test_6_market_review()  # 取消註解以啟用
        
        # 打印摘要
        tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
