#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dexter Eval Runner - 評測執行器
負責執行自動化評測並產出報告
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from tradingagents.meeting.orchestrator import MeetingOrchestrator
from .eval_models import TestCaseResult, EvalReport

logger = logging.getLogger("dexter_evals")

class DexterEvalRunner:
    def __init__(self, test_cases_path: str = "tests/dexter_evals/test_cases.json"):
        self.test_cases_path = Path(test_cases_path)
        self.orchestrator = MeetingOrchestrator()
        
    def load_test_cases(self) -> List[Dict[str, Any]]:
        with open(self.test_cases_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("test_cases", [])

    async def run_case(self, case: Dict[str, Any]) -> TestCaseResult:
        """執行單個測試案例"""
        start_time = time.time()
        test_id = case["id"]
        logger.info(f"🚀 正在執行測試案例: {test_id} - {case['query']}")
        
        # 模擬狀態
        success = False
        error_msg = None
        tool_usage = []
        
        try:
            # 這裡調用 orchestrator 但不使用 WebSocket emit
            # 未來可以進一步優化為 MockLLM 模式以節省成本
            scratchpad = await self.orchestrator._create_and_execute_plan(
                query=case["query"],
                market=case["market"],
                symbol_key=case["symbol_key"],
                emit=None # Headless mode
            )
            
            if scratchpad:
                success = True
                # 收集實際調用的工具
                tool_results = scratchpad.get_all_tool_results()
                tool_usage = [res.source_provider for res in tool_results.values()]
        except Exception as e:
            logger.error(f"❌ 測試案例 {test_id} 出錯: {e}")
            error_msg = str(e)

        duration = (time.time() - start_time) * 1000
        
        # 計算分數
        scores = self._calculate_scores(case, tool_usage)
        
        return TestCaseResult(
            test_id=test_id,
            query=case["query"],
            symbol_key=case["symbol_key"],
            success=success,
            duration_ms=duration,
            total_steps=len(tool_usage),
            tool_usage=tool_usage,
            tool_accuracy_score=scores["accuracy"],
            reasoning_score=scores["reasoning"],
            overall_score=scores["overall"],
            error=error_msg
        )

    def _calculate_scores(self, case: Dict[str, Any], actual_tools: List[str]) -> Dict[str, float]:
        """簡單的評分邏輯"""
        expected = set(case.get("expected_tools", []))
        actual = set(actual_tools)
        
        if not expected:
            accuracy = 100.0
        else:
            # 命中交集比例
            hit_count = len(expected.intersection(actual))
            accuracy = (hit_count / len(expected)) * 100.0
            
        # 推理分數 (暫定: 有調用工具即為基本推理成功)
        reasoning = 100.0 if len(actual) > 0 else 0.0
        
        # 總分加權
        overall = (accuracy * 0.7) + (reasoning * 0.3)
        
        return {
            "accuracy": accuracy,
            "reasoning": reasoning,
            "overall": overall
        }

    async def run_all(self) -> EvalReport:
        cases = self.load_test_cases()
        results = []
        start_time = datetime.now()
        
        for case in cases:
            result = await self.run_case(case)
            results.append(result)
            
        end_time = datetime.now()
        total = len(results)
        passed = sum(1 for r in results if r.success and r.overall_score >= 80)
        avg_score = sum(r.overall_score for r in results) / total if total > 0 else 0
        
        report = EvalReport(
            report_id=f"eval_{end_time.strftime('%Y%m%d_%H%M%S')}",
            start_time=start_time,
            end_time=end_time,
            total_cases=total,
            passed_cases=passed,
            failed_cases=total - passed,
            average_score=avg_score,
            results=results
        )
        
        self.save_report(report)
        return report

    def save_report(self, report: EvalReport):
        report_path = Path(f"tests/dexter_evals/reports/{report.report_id}.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report.json(ensure_ascii=False, indent=2))
        
        # 同步生成 Markdown 摘要
        md_path = report_path.with_suffix(".md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Dexter 評測報告: {report.report_id}\n\n")
            f.write(f"- **時間**: {report.start_time} - {report.end_time}\n")
            f.write(f"- **總案例**: {report.total_cases}\n")
            f.write(f"- **通率過**: {report.passed_cases}/{report.total_cases}\n")
            f.write(f"- **平均分**: {report.average_score:.2f}\n\n")
            f.write("## 詳細結果\n\n")
            f.write("| ID | 查詢 | 分數 | 狀態 | 工具使用 |\n")
            f.write("|---|---|---|---|---|\n")
            for r in report.results:
                status = "✅" if r.success and r.overall_score >= 80 else "❌"
                tools = ", ".join(r.tool_usage)
                f.write(f"| {r.test_id} | {r.query} | {r.overall_score:.1f} | {status} | {tools} |\n")

        logger.info(f"📊 評測報告已存儲: {report_path}")

if __name__ == "__main__":
    # 簡單的入口
    logging.basicConfig(level=logging.INFO)
    runner = DexterEvalRunner()
    asyncio.run(runner.run_all())
