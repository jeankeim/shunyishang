"""
推荐系统六维度不匹配专项审查

针对用户提出的 6 类不匹配问题，对全量测试用例逐条审查：
1. 性别不匹配：推荐物品的推断性别与用户性别相反
2. 温度不匹配：极端温度下厚度不当 / 高温长袖名称 / temperature_range 超限
3. 场景不匹配：违反 scene_mapping 排除规则（品类/关键词）或风格明显冲突
4. 功能不匹配：运动场景核心衣物缺运动功能、雨天推荐不耐水单品
5. 季节不匹配：推荐物品适用季节不含当前季节
6. 搭配完整性：推荐结果无法形成一套完整穿搭

判定口径全部复用生产代码（filters/scene_mapping/evaluator），避免双重标准。
"""

import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.api.tests.evaluation.data_generator import generate_all_data, TestCase
from apps.api.tests.evaluation.evaluator import score_outfit_completeness
from packages.recommendation.config import (
    EXTREME_HOT_TEMP, HOT_TEMP, EXTREME_COLD_TEMP, MILD_COLD_TEMP,
    get_effective_temperature,
)
from packages.recommendation.engine import score_and_rank_items
from packages.recommendation.filters import (
    infer_item_gender, is_hot_unfit_item,
    COLD_KEEP_NAME_KEYWORDS,
)
from packages.recommendation.scoring import infer_item_thickness
from packages.utils.scene_mapping import (
    get_scene_rules, is_style_scene_appropriate,
)

TOP_K = 5


def _run_case(tc: TestCase, items: List[Dict], user_gender: Optional[str]) -> List[Dict]:
    """与 run_evaluation.run_recommendation_for_case 一致，但支持性别参数"""
    user = tc.user
    use_bazi = tc.complexity in ("medium", "complex", "boundary")
    target_elements = user.target_elements if use_bazi else []
    boost_elements = user.boost_elements if use_bazi else None
    bazi_result = user.bazi_result if use_bazi else None

    enriched = []
    for item in items:
        item_copy = item.copy()
        base_semantic = item.get("semantic_score", 0.5)
        if target_elements:
            if item.get("primary_element") in target_elements:
                base_semantic = min(0.95, base_semantic + 0.2)
            elif item.get("secondary_element") in target_elements:
                base_semantic = min(0.9, base_semantic + 0.1)
        if user.style_preference and item.get("style") == user.style_preference:
            base_semantic = min(0.95, base_semantic + 0.25)
        item_copy["semantic_score"] = base_semantic
        enriched.append(item_copy)

    result = score_and_rank_items(
        items=enriched,
        target_elements=target_elements,
        boost_elements=boost_elements,
        bazi_result=bazi_result,
        scene=tc.scene,
        sub_scene=None,
        weather_info=tc.weather_info,
        user_id=None,
        user_prefs=None,
        user_skin_tone=user.skin_tone,
        user_style_preference=user.style_preference,
        user_body_type=user.body_type,
        user_gender=user_gender,
        top_k=TOP_K,
        batch_index=0,
    )
    return result.get("top_items", [])


# ============================================================
# 各维度审查函数：返回问题描述列表（空=通过）
# ============================================================

def audit_gender(items: List[Dict], user_gender: str) -> List[str]:
    """维度1：性别不匹配"""
    issues = []
    for item in items:
        item_gender = infer_item_gender(item)
        if item_gender is not None and item_gender != user_gender:
            issues.append(
                f"{user_gender}性用户收到{item_gender}款: "
                f"{item.get('name')}(gender={item.get('gender')},cat={item.get('category')})"
            )
    return issues


def _temp_violations(temp: float, item: Dict) -> List[str]:
    """单物品的温度问题（厚度 + 高温长袖名称 + temperature_range 超限）"""
    problems = []
    thickness = infer_item_thickness(item)
    name = item.get("name") or ""
    if temp >= HOT_TEMP and thickness in ("厚重", "中厚"):
        problems.append(f"{temp}°C高温推荐{thickness}: {name}")
    elif temp <= EXTREME_COLD_TEMP and thickness in ("极薄", "轻薄"):
        problems.append(f"{temp}°C严寒推荐{thickness}: {name}")
    elif temp <= MILD_COLD_TEMP and thickness == "极薄":
        problems.append(f"{temp}°C低温推荐极薄: {name}")
    if is_hot_unfit_item(item, temp):
        problems.append(f"{temp}°C高温推荐长袖/保暖类: {name}")
    temp_range = item.get("temperature_range")
    if isinstance(temp_range, dict):
        range_max = temp_range.get("最高") or temp_range.get("max")
        range_min = temp_range.get("最低") or temp_range.get("min")
        try:
            if range_max is not None and temp > int(range_max) + 8:
                problems.append(f"{temp}°C超最高适用{range_max}°C: {name}")
        except (ValueError, TypeError):
            pass
        try:
            if range_min is not None and temp < int(range_min) - 10:
                problems.append(f"{temp}°C低于最低适用{range_min}°C: {name}")
        except (ValueError, TypeError):
            pass
    return problems


def audit_temperature(items: List[Dict], weather_info: Optional[Dict]) -> List[str]:
    """维度2：温度不匹配"""
    if not weather_info:
        return []
    temp = get_effective_temperature(weather_info)
    if temp is None:
        return []
    issues = []
    for item in items:
        issues.extend(_temp_violations(temp, item))
    return issues


def audit_scene(items: List[Dict], scene: Optional[str], weather_info: Optional[Dict] = None) -> List[str]:
    """维度3：场景不匹配（品类/关键词硬规则 + 风格冲突）

    硬违规与风格冲突分开标记，便于报告区分严重度。
    与生产 apply_scene_hard_filter 口径一致：≤10°C 时保暖单品
    （羽绒服/大衣等）不因场景关键词计为硬违规（保暖优先于风格）。
    """
    if not scene:
        return []
    issues = []
    temp = get_effective_temperature(weather_info)
    cold_exempt = temp is not None and temp <= MILD_COLD_TEMP
    rules = get_scene_rules(scene)
    if rules:
        excluded_cats = set(rules.get("excluded_categories", []))
        excluded_kws = tuple(rules.get("excluded_keywords", []))
        for item in items:
            name = item.get("name") or ""
            if item.get("category") in excluded_cats:
                issues.append(f"[硬] {scene}场景推荐排除品类[{item.get('category')}]: {name}")
            elif cold_exempt and any(k in name for k in COLD_KEEP_NAME_KEYWORDS):
                continue  # 低温保暖豁免，与生产一致
            elif excluded_kws and any(k in name for k in excluded_kws):
                hit = [k for k in excluded_kws if k in name]
                issues.append(f"[硬] {scene}场景推荐排除关键词{hit}: {name}")
    for item in items:
        if not is_style_scene_appropriate(item, scene):
            issues.append(
                f"[风格] {scene}场景风格冲突(style={item.get('style')}): {item.get('name')}"
            )
    return issues


SPORT_FUNCS = ("透气", "速干", "运动", "弹性")
CORE_CATEGORIES = {"上装", "下装", "鞋履"}
RAIN_UNFIT_KEYWORDS = ("帆布", "绒面", "麂皮", "真丝", "棉麻")


def audit_functionality(items: List[Dict], tc: TestCase) -> List[str]:
    """维度4：功能不匹配（运动功能缺失 / 雨天不耐水）

    运动功能检查仅在有效温度>=15°C时执行：低温下引擎正确优先保暖，
    候选池无保暖运动单品时推保暖便服是合理降级，不计为问题。
    """
    issues = []
    if tc.scene == "运动":
        temp = get_effective_temperature(tc.weather_info)
        if temp is None or temp >= 15:
            for item in items:
                if item.get("category") not in CORE_CATEGORIES:
                    continue
                funcs = item.get("functionality") or []
                if isinstance(funcs, dict):
                    funcs = [k for k, v in funcs.items() if v]
                if not any(f in funcs for f in SPORT_FUNCS):
                    issues.append(f"运动场景核心单品无运动功能: {item.get('name')}")
    weather_desc = (tc.weather_info or {}).get("weather_desc", "")
    if "雨" in weather_desc:
        for item in items:
            name = item.get("name") or ""
            if item.get("category") == "鞋履" and any(k in name for k in RAIN_UNFIT_KEYWORDS):
                issues.append(f"雨天推荐不耐水鞋履: {name}")
    return issues


def audit_season(items: List[Dict], season: str, weather_info: Optional[Dict]) -> List[str]:
    """维度5：季节不匹配（按温度适宜季节集判定，与生产季节护栏口径一致）

    规则：
    - ≤10°C：衣物必须含秋/冬适用标记
    - 10~20°C：夏季专属（仅含夏）不适宜
    - ≥30°C：必须含夏
    - 无温度信息时退化为与用例季节标签比对
    """
    issues = []
    temp = get_effective_temperature(weather_info)
    for item in items:
        seasons = item.get("applicable_seasons") or []
        if isinstance(seasons, str):
            try:
                seasons = json.loads(seasons)
            except (ValueError, TypeError):
                seasons = []
        if not seasons:
            continue
        season_set = set(seasons)
        if temp is not None:
            if temp <= 10 and not ({"秋", "冬"} & season_set):
                issues.append(f"低温({temp}°C)推荐无秋冬适用标记的单品({seasons}): {item.get('name')}")
            elif temp < 20 and season_set == {"夏"}:
                issues.append(f"非高温({temp}°C)推荐夏季专属单品: {item.get('name')}")
            elif temp >= 30 and "夏" not in season_set:
                issues.append(f"极热({temp}°C)推荐不含夏季的单品({seasons}): {item.get('name')}")
        elif season not in season_set:
            issues.append(f"{season}季推荐适用{seasons}的单品: {item.get('name')}")
    return issues


def audit_outfit(items: List[Dict]) -> List[str]:
    """维度6：搭配完整性（仅标记无法组成一套穿搭的严重问题）

    判定：缺上半身/缺下半身/未匹配任何有效搭配模式。
    （缺少鞋履/外套/点缀属优化项，不计为“不成套”）
    """
    result = score_outfit_completeness(items)
    if not result["matched_pattern"] or not result["has_top"] or not result["has_bottom"]:
        detail = "; ".join(result["issues"]) or "搭配模式未匹配"
        return [f"搭配不成套({result['total']}/10, 分布{result['category_distribution']}): {detail}"]
    return []


# ============================================================
# 主流程
# ============================================================

def main():
    random.seed(42)
    print("=" * 70)
    print("🔍 推荐系统六维度不匹配专项审查")
    print("=" * 70)

    data = generate_all_data()
    items, test_cases = data["items"], data["test_cases"]
    print(f"\n审查规模: {len(test_cases)} 个用例 × top-{TOP_K} 推荐\n")

    dims = ["性别", "温度", "场景", "功能", "季节", "搭配"]
    dim_issues: Dict[str, List[str]] = defaultdict(list)
    dim_case_hits: Dict[str, set] = defaultdict(set)
    issue_counter: Dict[str, Counter] = defaultdict(Counter)
    # 对照组：不传性别时的泄漏量（量化性别安全网效果）
    gender_leak_without_net = 0

    start = time.time()
    for tc in test_cases:
        recs = _run_case(tc, items, user_gender=tc.user.gender)
        for dim, issues in zip(dims, [
            audit_gender(recs, tc.user.gender),
            audit_temperature(recs, tc.weather_info),
            audit_scene(recs, tc.scene, tc.weather_info),
            audit_functionality(recs, tc),
            audit_season(recs, tc.season, tc.weather_info),
            audit_outfit(recs),
        ]):
            if issues:
                dim_case_hits[dim].add(tc.case_id)
                dim_issues[dim].extend(f"[{tc.case_id}|{tc.description}] {i}" for i in issues)
                for i in issues:
                    # 按最后一个冒号前的模式归类，剥离具体单品名便于统计
                    issue_counter[dim][i.rsplit(": ", 1)[0]] += 1

        # 对照组：无性别安全网
        recs_no_net = _run_case(tc, items, user_gender=None)
        for item in recs_no_net:
            g = infer_item_gender(item)
            if g is not None and g != tc.user.gender:
                gender_leak_without_net += 1

    elapsed = time.time() - start
    total = len(test_cases)

    print("=" * 70)
    print(f"📋 审查结果（耗时 {elapsed:.1f}s）")
    print("=" * 70)
    for dim in dims:
        n_cases = len(dim_case_hits[dim])
        n_issues = len(dim_issues[dim])
        rate = n_cases / total * 100
        status = "✅" if n_issues == 0 else "⚠️ "
        print(f"\n{status} 维度[{dim}] 问题条数={n_issues}，涉及用例={n_cases}/{total} ({rate:.2f}%)")
        if dim_issues[dim]:
            # Top 问题模式
            print("   Top 问题模式:")
            for pattern, cnt in issue_counter[dim].most_common(8):
                print(f"     ×{cnt}  {pattern[:100]}")
            print("   示例（前5条）:")
            for line in dim_issues[dim][:5]:
                print(f"     - {line[:150]}")

    print("\n" + "-" * 70)
    print(f"🧪 性别安全网对照实验（{total} 用例）:")
    print(f"   不传性别(模拟安全网缺失): 性别错配物品 {gender_leak_without_net} 件次")
    print(f"   传入性别(生产行为): 性别错配物品 {len(dim_issues['性别'])} 件次")
    print("-" * 70)

    report = {
        "total_cases": total,
        "elapsed_seconds": round(elapsed, 1),
        "dimensions": {
            dim: {
                "issue_count": len(dim_issues[dim]),
                "affected_cases": len(dim_case_hits[dim]),
                "affected_rate_pct": round(len(dim_case_hits[dim]) / total * 100, 2),
                "top_patterns": [
                    {"pattern": p, "count": c}
                    for p, c in issue_counter[dim].most_common(10)
                ],
                "samples": dim_issues[dim][:20],
            } for dim in dims
        },
        "gender_safety_net_experiment": {
            "leak_without_net": gender_leak_without_net,
            "leak_with_net": len(dim_issues["性别"]),
        },
    }
    out_path = Path(__file__).parent / "dimension_audit_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 报告已保存: {out_path}")


if __name__ == "__main__":
    main()
