# -*- coding: utf-8 -*-
"""
Base Solver Diagnostics — Software-agnostic failure analysis.
求解诊断器基类 — 软件无关的失败分析。

To customize, override ERROR_PATTERNS with software-specific entries.
要定制，用软件专属条目覆盖 ERROR_PATTERNS。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DiagnosticsReport:
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    quality_score: float = 1.0
    details: dict = field(default_factory=dict)


class BaseDiagnostics:
    """Base diagnostics with pluggable error patterns."""

    # === Override this for each software / 为每个软件覆盖此项 ===
    ERROR_PATTERNS: list[tuple] = [
        (r"(?i)error|fail", "unknown_error", "Unknown error — check logs"),
    ]

    def diagnose(self, result: dict) -> DiagnosticsReport:
        if result.get("success"):
            return self._diagnose_success(result)
        return self._diagnose_failure(result)

    def _diagnose_failure(self, result: dict) -> DiagnosticsReport:
        error_msg = result.get("error", str(result))
        report = DiagnosticsReport(success=False, errors=[error_msg])
        for pattern, code, suggestion in self.ERROR_PATTERNS:
            if re.search(pattern, error_msg, re.IGNORECASE):
                report.suggestions.append(suggestion)
                report.details["error_code"] = code
                break
        if not report.suggestions:
            report.suggestions = ["Check full log", "Try simplest version", "Verify manually"]
        report.quality_score = 0.0
        return report

    def _diagnose_success(self, result: dict) -> DiagnosticsReport:
        report = DiagnosticsReport(success=True)
        if "warnings" in result and result["warnings"]:
            report.warnings = result["warnings"]
        return report

    def validate_values(self, values: list[float], label: str = "values", min_expected: float = None, max_expected: float = None) -> DiagnosticsReport:
        """Generic value validation / 通用数值验证."""
        report = DiagnosticsReport(success=True)
        if min_expected is not None and any(v < min_expected for v in values):
            report.warnings.append(f"{label}: some values below {min_expected}")
            report.quality_score -= 0.2
        if max_expected is not None and any(v > max_expected for v in values):
            report.warnings.append(f"{label}: some values above {max_expected}")
            report.quality_score -= 0.2
        report.quality_score = max(0, report.quality_score)
        return report


class ResultValidator:
    """Compare simulation results with paper/expected values.
    仿真结果与论文/预期值对比。"""

    def compare(self, simulated: dict, expected: dict) -> dict:
        comparisons = []
        passed = 0
        failed = 0
        for param, exp in expected.items():
            if param not in simulated:
                comparisons.append({"parameter": param, "status": "missing"})
                failed += 1
                continue
            sim_val = simulated[param]
            exp_val = exp if isinstance(exp, (int, float)) else exp.get("value", exp)
            tolerance = exp.get("tolerance", 0.05) if isinstance(exp, dict) else 0.05
            if exp_val == 0:
                match = abs(sim_val) < tolerance
            else:
                match = abs(sim_val - exp_val) / abs(exp_val) < tolerance
            comparisons.append({"parameter": param, "simulated": sim_val, "expected": exp_val, "deviation": abs(sim_val - exp_val) / (abs(exp_val) + 1e-9), "match": match})
            if match: passed += 1
            else: failed += 1
        return {"summary": f"{passed}/{passed+failed} match", "passed": passed, "failed": failed, "details": comparisons, "all_match": failed == 0}
