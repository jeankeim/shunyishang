"""
推荐算法 CI 质量门禁

基于 run_evaluation.py 的评分报告，对各维度阈值执行断言，
产出通过/失败清单，并以退出码驱动 CI（0=通过，1=失败）。

使用方式：
    # 本地全量跑
    python -m apps.api.tests.evaluation.ci_gate

    # CI 快速门禁（采样 + 输出 JSON 工件）
    python -m apps.api.tests.evaluation.ci_gate --sample 200 --json gate_report.json

    # 严格模式（把"警告级"检查也升级为阻断）
    python -m apps.api.tests.evaluation.ci_gate --strict

阈值来源：与 evaluator.py 的 100 分五维评分体系、outfit_completeness_stats
及 run_evaluation.py 的评级带（A>=90 / B>=80 / C>=70）对齐。
所有阈值可通过命令行覆盖，便于按发版阶段收紧。
"""

import sys
import json
import argparse
from dataclasses import dataclass, field, asdict
from typing import Callable, Dict, List, Optional
from pathlib import Path

# 添加项目根目录到路径（与 run_evaluation.py 保持一致）
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.api.tests.evaluation.run_evaluation import run_evaluation


# ============================================================
# 默认阈值配置（可通过 CLI 覆盖）
#
# 校准原则：阀值 = 当前全量基线下方留 3~5 分防回退余量。
# 目标是“守住水位 + 捕捉真实退化”，而非“开箱即红”。
# 随着算法迭代，应周期性上调（棘轮）。
#
# 基线快照（全量 3520 用例，物品池 116 件）：
#   综合 93.99 | 多样性 95.3% | 合理性 92.8% | 理由 92.8%
#   常识 96.4% | 个性化 92.2% | 搭配匹配率 94.9% | 集中度问题 0.6%
#   上半身覆盖 95.9% | 下半身覆盖 96.2% | 边界均分 90.6 | 温度违规 0
# ============================================================
DEFAULT_THRESHOLDS: Dict[str, float] = {
    # ---- 全局综合分（基线 93.99，守住高分水位） ----
    "min_avg_total_score": 90.0,        # 综合得分 >= 90
    "max_below_70_ratio": 3.0,          # 待改进(<70)用例占比 <= 3%（基线 0%）

    # ---- 五维达标率（%），对齐 dimension_stats.avg_ratio ----
    "min_ratio_物品多样性": 90.0,      # 基线 95.3
    "min_ratio_物品合理性": 88.0,      # 基线 92.8
    "min_ratio_推荐理由质量": 88.0,    # 基线 92.8
    "min_ratio_常识符合度": 92.0,      # 基线 96.4（承载温度安全，阀值偏高）
    "min_ratio_个性化精准度": 88.0,    # 基线 92.2

    # ---- 搭配完整性专项 ----
    "min_pattern_match_rate": 92.0,     # 基线 94.9
    "max_concentration_issue_rate": 5.0,  # 基线 0.6
    "min_coverage_top": 93.0,           # 上半身覆盖率，基线 95.9
    "min_coverage_bottom": 93.0,        # 下半身覆盖率，基线 96.2

    # ---- 复杂度稳定性（各档平均分下限） ----
    "min_complexity_avg": 85.0,         # 每个复杂度档平均分 >= 85（最低档 complex 90.7）
    "min_boundary_avg": 85.0,           # 边界用例平均分 >= 85（基线 90.6）

    # ---- 安全红线（critical）----
    "max_temp_violations": 0,           # 温度常识违规数必须为 0
}


# ============================================================
# 检查项数据结构
# ============================================================
@dataclass
class Check:
    name: str
    category: str
    actual: float
    op: str            # ">=" | "<=" | "=="
    threshold: float
    critical: bool = False
    passed: bool = field(init=False, default=False)

    def evaluate(self) -> bool:
        if self.op == ">=":
            self.passed = self.actual >= self.threshold
        elif self.op == "<=":
            self.passed = self.actual <= self.threshold
        elif self.op == "==":
            self.passed = self.actual == self.threshold
        else:
            raise ValueError(f"未知比较符: {self.op}")
        return self.passed

    def as_row(self) -> Dict:
        return {
            "name": self.name,
            "category": self.category,
            "actual": self.actual,
            "op": self.op,
            "threshold": self.threshold,
            "critical": self.critical,
            "passed": self.passed,
        }


# ============================================================
# 温度安全违规统计
# ============================================================
def count_temp_violations(results) -> int:
    """
    统计逐用例结果中的温度类违规数。

    evaluator.evaluate_single_case 会把 _check_temp_violation /
    _check_temp_range_violation 产生的违规原样写入 result.issues，
    其文案均包含 '°C'（搭配类问题不含 °C），据此计数。
    """
    count = 0
    for r in results:
        for issue in getattr(r, "issues", []):
            if "°C" in issue:
                count += 1
    return count


# ============================================================
# 构建检查清单
# ============================================================
def build_checks(report: Dict, temp_violations: int, th: Dict[str, float]) -> List[Check]:
    checks: List[Check] = []

    # ---- 全局综合分 ----
    checks.append(Check(
        "综合得分", "全局",
        round(report.get("avg_total_score", 0.0), 2),
        ">=", th["min_avg_total_score"], critical=True,
    ))

    total_cases = report.get("total_cases", 0) or 1
    below_70 = report.get("score_distribution", {}).get("below_70", 0)
    below_70_ratio = round(below_70 / total_cases * 100, 1)
    checks.append(Check(
        "待改进(<70)用例占比%", "全局",
        below_70_ratio, "<=", th["max_below_70_ratio"],
    ))

    # ---- 五维达标率 ----
    dim_stats = report.get("dimension_stats", {})
    dim_threshold_keys = {
        "物品多样性": "min_ratio_物品多样性",
        "物品合理性": "min_ratio_物品合理性",
        "推荐理由质量": "min_ratio_推荐理由质量",
        "常识符合度": "min_ratio_常识符合度",
        "个性化精准度": "min_ratio_个性化精准度",
    }
    for dim_name, key in dim_threshold_keys.items():
        ratio = dim_stats.get(dim_name, {}).get("avg_ratio", 0.0)
        # 常识符合度承载温度安全，视为 critical
        is_critical = dim_name == "常识符合度"
        checks.append(Check(
            f"{dim_name}达标率%", "五维",
            ratio, ">=", th[key], critical=is_critical,
        ))

    # ---- 搭配完整性专项 ----
    outfit = report.get("outfit_completeness_stats", {})
    if outfit and "error" not in outfit:
        checks.append(Check(
            "搭配模式匹配率%", "搭配完整性",
            outfit.get("pattern_match_rate", 0.0), ">=", th["min_pattern_match_rate"],
        ))
        checks.append(Check(
            "集中度问题率%", "搭配完整性",
            outfit.get("concentration_issue_rate", 100.0), "<=", th["max_concentration_issue_rate"],
        ))
        coverage = outfit.get("coverage_rates", {})
        # 覆盖率字段名带括号说明，用前缀匹配定位
        top_rate = _find_coverage(coverage, "上半身")
        bottom_rate = _find_coverage(coverage, "下半身")
        checks.append(Check(
            "上半身覆盖率%", "搭配完整性",
            top_rate, ">=", th["min_coverage_top"], critical=True,
        ))
        checks.append(Check(
            "下半身覆盖率%", "搭配完整性",
            bottom_rate, ">=", th["min_coverage_bottom"], critical=True,
        ))

    # ---- 复杂度稳定性 ----
    complexity_stats = report.get("complexity_stats", {})
    for comp, cstats in complexity_stats.items():
        avg = cstats.get("avg_score", 0.0)
        if comp == "boundary":
            checks.append(Check(
                f"复杂度[{comp}]平均分", "复杂度稳定性",
                round(avg, 2), ">=", th["min_boundary_avg"], critical=True,
            ))
        else:
            checks.append(Check(
                f"复杂度[{comp}]平均分", "复杂度稳定性",
                round(avg, 2), ">=", th["min_complexity_avg"],
            ))

    # ---- 安全红线：温度违规数 ----
    checks.append(Check(
        "温度常识违规数", "安全红线",
        temp_violations, "<=", th["max_temp_violations"], critical=True,
    ))

    return checks


def _find_coverage(coverage: Dict, prefix: str) -> float:
    """coverage_rates 的 key 形如 '上半身(上装/裙装)'，按前缀匹配取值。"""
    for k, v in coverage.items():
        if k.startswith(prefix):
            return v
    return 0.0


# ============================================================
# 报告打印
# ============================================================
import unicodedata


def _dw(s: str) -> int:
    """计算字符串的显示宽度（东亚全角字符计 2）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1 for ch in s)


def _pad(s: str, width: int, align: str = "left") -> str:
    """宽度感知的对齐（兼容中英混排）。"""
    s = str(s)
    gap = max(0, width - _dw(s))
    return (" " * gap + s) if align == "right" else (s + " " * gap)


def print_gate_report(checks: List[Check], strict: bool) -> bool:
    print("\n" + "=" * 72)
    print("🚦 推荐算法 CI 质量门禁")
    print("=" * 72)

    header = (
        _pad("状态", 8) + _pad("类别", 14) + _pad("检查项", 26)
        + _pad("实测", 10, "right") + "  " + _pad("判据", 14) + _pad("级别", 6)
    )
    print(header)
    print("-" * 72)

    hard_failures: List[Check] = []
    soft_failures: List[Check] = []

    current_category = None
    for c in checks:
        c.evaluate()
        status = "✅ PASS" if c.passed else "❌ FAIL"
        level = "阻断" if c.critical else "警告"
        cat = c.category if c.category != current_category else ""
        current_category = c.category
        criterion = f"{c.op} {c.threshold}"
        print(
            _pad(status, 8) + _pad(cat, 14) + _pad(c.name, 26)
            + _pad(c.actual, 10, "right") + "  " + _pad(criterion, 14) + _pad(level, 6)
        )

        if not c.passed:
            # strict 模式下警告级也升级为阻断
            if c.critical or strict:
                hard_failures.append(c)
            else:
                soft_failures.append(c)

    print("-" * 72)
    passed_count = sum(1 for c in checks if c.passed)
    print(f"总计 {len(checks)} 项，通过 {passed_count} 项，失败 {len(checks) - passed_count} 项")

    if soft_failures and not strict:
        print(f"\n⚠️  警告级失败 {len(soft_failures)} 项（非严格模式，不阻断合并）：")
        for c in soft_failures:
            print(f"   - {c.name}: 实测 {c.actual} {c.op} {c.threshold} 未满足")

    gate_pass = len(hard_failures) == 0
    if gate_pass:
        mode = "严格" if strict else "标准"
        print(f"\n🟢 门禁通过（{mode}模式）")
    else:
        print(f"\n🔴 门禁失败：{len(hard_failures)} 项阻断级检查未通过")
        for c in hard_failures:
            print(f"   ✗ [{c.category}] {c.name}: 实测 {c.actual}，要求 {c.op} {c.threshold}")

    print("=" * 72)
    return gate_pass


# ============================================================
# 主入口
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(description="推荐算法 CI 质量门禁")
    parser.add_argument("--sample", type=int, default=None,
                        help="采样数量（默认全量；CI 快速门禁建议 200）")
    parser.add_argument("--strict", action="store_true",
                        help="严格模式：警告级失败也阻断（退出码 1）")
    parser.add_argument("--json", type=str, default=None,
                        help="将门禁结果写入指定 JSON 文件（CI 工件）")
    parser.add_argument("--quiet", action="store_true",
                        help="静默模式：不打印底层评估的详细过程日志")

    # 允许覆盖任意阈值：--set min_avg_total_score=82
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                        help="覆盖阈值，可重复，如 --set min_avg_total_score=82")

    args = parser.parse_args()

    thresholds = dict(DEFAULT_THRESHOLDS)
    for kv in args.set:
        if "=" not in kv:
            print(f"⚠️  忽略非法 --set 参数: {kv}")
            continue
        key, value = kv.split("=", 1)
        key = key.strip()
        if key not in thresholds:
            print(f"⚠️  未知阈值键: {key}（可用键: {', '.join(thresholds)}）")
            continue
        try:
            thresholds[key] = float(value)
        except ValueError:
            print(f"⚠️  阈值必须为数字: {kv}")

    # 运行评估，拿到聚合报告 + 逐用例结果
    report, results = run_evaluation(
        sample_size=args.sample,
        verbose=not args.quiet,
        return_results=True,
    )

    temp_violations = count_temp_violations(results)
    checks = build_checks(report, temp_violations, thresholds)
    gate_pass = print_gate_report(checks, strict=args.strict)

    if args.json:
        artifact = {
            "gate_pass": gate_pass,
            "strict": args.strict,
            "avg_total_score": report.get("avg_total_score"),
            "temp_violations": temp_violations,
            "thresholds": thresholds,
            "checks": [c.as_row() for c in checks],
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(artifact, f, ensure_ascii=False, indent=2)
        print(f"\n💾 门禁工件已保存: {args.json}")

    return 0 if gate_pass else 1


if __name__ == "__main__":
    sys.exit(main())
