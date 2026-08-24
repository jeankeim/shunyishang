"""
推荐算法评估主运行器

执行完整的评估流程：
1. 生成测试数据集
2. 对每个测试用例运行推荐引擎
3. 评估推荐结果
4. 输出评分报告
"""

import sys
import time
import json
from typing import Dict, List
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.api.tests.evaluation.data_generator import (
    generate_all_data,
    VirtualUser,
    TestCase,
)
from apps.api.tests.evaluation.evaluator import (
    evaluate_single_case,
    aggregate_results,
    EvaluationResult,
)
from packages.recommendation.engine import score_and_rank_items


def run_recommendation_for_case(
    test_case: TestCase,
    items: List[Dict],
    top_k: int = 5,
) -> List[Dict]:
    """
    对单个测试用例运行推荐引擎
    
    Args:
        test_case: 测试用例
        items: 物品池
        top_k: 返回数量
    
    Returns:
        推荐的 top-k 物品列表
    """
    user = test_case.user
    
    # 根据复杂度决定是否使用八字
    use_bazi = test_case.complexity in ("medium", "complex", "boundary")
    
    # 准备参数
    target_elements = user.target_elements if use_bazi else []
    boost_elements = user.boost_elements if use_bazi else None
    bazi_result = user.bazi_result if use_bazi else None
    
    # 审美参数（始终传入，模拟生产环境用户画像始终可用）
    skin_tone = user.skin_tone
    style_pref = user.style_preference
    body_type = user.body_type
    
    # 为物品添加模拟的语义分（基于五行匹配度 + 风格偏好）
    enriched_items = []
    for item in items:
        item_copy = item.copy()
        # 模拟语义检索：五行匹配的物品语义分更高
        base_semantic = item.get("semantic_score", 0.5)
        if target_elements:
            if item.get("primary_element") in target_elements:
                base_semantic = min(0.95, base_semantic + 0.2)
            elif item.get("secondary_element") in target_elements:
                base_semantic = min(0.9, base_semantic + 0.1)
        # 模拟语义检索：风格匹配的物品语义分更高（生产环境向量检索会考虑用户风格偏好）
        if style_pref and item.get("style") == style_pref:
            base_semantic = min(0.95, base_semantic + 0.25)
        item_copy["semantic_score"] = base_semantic
        enriched_items.append(item_copy)
    
    # 调用推荐引擎（透传性别，与生产链路一致：评分后性别硬过滤安全网生效）
    result = score_and_rank_items(
        items=enriched_items,
        target_elements=target_elements,
        boost_elements=boost_elements,
        bazi_result=bazi_result,
        scene=test_case.scene,
        sub_scene=None,
        weather_info=test_case.weather_info,
        user_id=None,  # 不使用行为数据
        user_prefs=None,
        user_skin_tone=skin_tone,
        user_style_preference=style_pref,
        user_body_type=body_type,
        user_gender=user.gender,
        top_k=top_k,
        batch_index=0,
    )
    
    return result.get("top_items", [])


def run_evaluation(
    sample_size: int = None,
    verbose: bool = True,
    return_results: bool = False,
):
    """
    运行完整评估
    
    Args:
        sample_size: 采样数量（None=全量）
        verbose: 是否输出详细日志
        return_results: 为 True 时额外返回逐用例结果列表（供 CI 门禁统计安全违规）
    
    Returns:
        - return_results=False（默认）: 评估报告字典（向后兼容）
        - return_results=True: (评估报告字典, 逐用例 EvaluationResult 列表)
    """
    print("=" * 60)
    print("🎯 推荐算法评估系统")
    print("=" * 60)
    
    # 1. 生成测试数据
    print("\n📦 步骤1：生成测试数据集...")
    start_time = time.time()
    data = generate_all_data()
    gen_time = time.time() - start_time
    
    items = data["items"]
    users = data["users"]
    test_cases = data["test_cases"]
    stats = data["stats"]
    
    if verbose:
        print(f"   物品池: {stats['total_items']} 件")
        print(f"   虚拟用户: {stats['total_users']} 人")
        print(f"   测试用例: {stats['total_cases']} 个")
        print(f"   复杂度分布: {stats['complexity_distribution']}")
        print(f"   生成耗时: {gen_time:.2f}s")
    
    # 采样（如果需要）
    if sample_size and sample_size < len(test_cases):
        import random
        random.seed(42)
        test_cases = random.sample(test_cases, sample_size)
        if verbose:
            print(f"\n   📌 采样模式: 从 {stats['total_cases']} 个用例中抽取 {sample_size} 个")
    
    # 2. 运行推荐引擎
    print(f"\n🚀 步骤2：运行推荐引擎（{len(test_cases)} 个用例）...")
    start_time = time.time()
    
    results: List[EvaluationResult] = []
    progress_interval = max(1, len(test_cases) // 20)
    
    for idx, tc in enumerate(test_cases):
        # 运行推荐
        recommended = run_recommendation_for_case(tc, items, top_k=5)
        
        # 评估
        user_info = {
            "target_elements": tc.user.target_elements,
            "skin_tone": tc.user.skin_tone,
            "body_type": tc.user.body_type,
            "style_preference": tc.user.style_preference,
        }
        
        eval_result = evaluate_single_case(
            case_id=tc.case_id,
            user_id=tc.user.user_id,
            complexity=tc.complexity,
            recommended_items=recommended,
            user_info=user_info,
            weather_info=tc.weather_info,
            scene=tc.scene,
            season=tc.season,
        )
        results.append(eval_result)
        
        # 进度输出
        if verbose and (idx + 1) % progress_interval == 0:
            progress = (idx + 1) / len(test_cases) * 100
            print(f"   进度: {progress:.0f}% ({idx + 1}/{len(test_cases)})")
    
    run_time = time.time() - start_time
    if verbose:
        print(f"   ✓ 完成，耗时: {run_time:.2f}s")
    
    # 3. 汇总结果
    print("\n📊 步骤3：汇总评估结果...")
    report = aggregate_results(results)
    report["execution_time"] = round(run_time, 2)
    report["data_generation_time"] = round(gen_time, 2)
    
    # 4. 输出报告
    print_report(report)
    
    if return_results:
        return report, results
    return report


def print_report(report: Dict):
    """打印评估报告"""
    print("\n" + "=" * 60)
    print("📋 推荐算法评估报告")
    print("=" * 60)
    
    print(f"\n📌 测试规模: {report['total_cases']} 个用例")
    print(f"⏱️  执行耗时: {report.get('execution_time', 0)}s")
    
    # 总分
    avg_score = report["avg_total_score"]
    print(f"\n🏆 综合得分: {avg_score:.2f} / 100")
    
    # 评级
    if avg_score >= 90:
        grade = "优秀 (A)"
    elif avg_score >= 80:
        grade = "良好 (B)"
    elif avg_score >= 70:
        grade = "中等 (C)"
    else:
        grade = "待改进 (D)"
    print(f"📊 评级: {grade}")
    
    # 分数分布
    dist = report["score_distribution"]
    print(f"\n📈 分数分布:")
    print(f"   优秀 (90-100): {dist['excellent_90_100']} 个 ({dist['excellent_90_100']/report['total_cases']*100:.1f}%)")
    print(f"   良好 (80-89):  {dist['good_80_89']} 个 ({dist['good_80_89']/report['total_cases']*100:.1f}%)")
    print(f"   中等 (70-79):  {dist['average_70_79']} 个 ({dist['average_70_79']/report['total_cases']*100:.1f}%)")
    print(f"   待改进 (<70):  {dist['below_70']} 个 ({dist['below_70']/report['total_cases']*100:.1f}%)")
    
    # 各维度得分
    print(f"\n📐 各维度得分:")
    print("-" * 50)
    for dim_name, dim_stats in report["dimension_stats"].items():
        bar_len = int(dim_stats["avg_ratio"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"   {dim_name}: {dim_stats['avg_score']:.1f}/{dim_stats['max_possible']:.0f} ({dim_stats['avg_ratio']:.1f}%) {bar}")
    print("-" * 50)
    
    # 搭配完整性专项报告
    outfit_stats = report.get("outfit_completeness_stats", {})
    if outfit_stats and "error" not in outfit_stats:
        print(f"\n👔 搭配完整性专项评估:")
        print("-" * 50)
        print(f"   搭配得分: {outfit_stats['avg_outfit_score']:.2f}/{outfit_stats['max_possible']} ({outfit_stats['avg_ratio']:.1f}%)")
        print(f"   搭配模式匹配率: {outfit_stats['pattern_match_rate']:.1f}%")
        print(f"   集中度问题率: {outfit_stats['concentration_issue_rate']:.1f}%")
        print(f"   部位覆盖率:")
        for part, rate in outfit_stats.get("coverage_rates", {}).items():
            bar_len = int(rate / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"     {part}: {rate:.1f}% {bar}")
        print("-" * 50)
    
    # 按复杂度统计
    print(f"\n🎚️  按复杂度统计:")
    complexity_names = {
        "simple": "简单场景",
        "medium": "中等场景",
        "complex": "复杂场景",
        "boundary": "边界测试",
    }
    for comp, comp_stats in report["complexity_stats"].items():
        name = complexity_names.get(comp, comp)
        print(f"   {name}: {comp_stats['count']}个, 平均{comp_stats['avg_score']:.1f}分, 范围[{comp_stats['min_score']:.1f}, {comp_stats['max_score']:.1f}]")
    
    # 问题统计
    if report["total_issues"] > 0:
        print(f"\n⚠️  发现问题: {report['total_issues']} 个")
        print("   示例问题:")
        for issue in report["sample_issues"][:5]:
            print(f"   - {issue}")
    
    print("\n" + "=" * 60)


def save_report(report: Dict, filepath: str = None):
    """保存报告到JSON文件"""
    if filepath is None:
        filepath = str(Path(__file__).parent / "evaluation_report.json")
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n💾 报告已保存: {filepath}")


# ============================================================
# 用户档案导出
# ============================================================

def export_user_profiles(users: List[VirtualUser], filepath: str = None):
    """导出用户档案"""
    if filepath is None:
        filepath = str(Path(__file__).parent / "user_profiles.json")
    
    profiles = []
    for user in users:
        profiles.append({
            "user_id": user.user_id,
            "gender": user.gender,
            "day_master": user.day_master,
            "strength": user.strength,
            "target_elements": user.target_elements,
            "avoid_elements": user.avoid_elements,
            "boost_elements": user.boost_elements,
            "skin_tone": user.skin_tone,
            "body_type": user.body_type,
            "style_preference": user.style_preference,
        })
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)
    print(f"💾 用户档案已保存: {filepath}")


# ============================================================
# 主入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="推荐算法评估系统")
    parser.add_argument("--sample", type=int, default=None, help="采样数量（默认全量）")
    parser.add_argument("--save", action="store_true", help="保存报告到文件")
    parser.add_argument("--export-users", action="store_true", help="导出用户档案")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    args = parser.parse_args()
    
    # 运行评估
    report = run_evaluation(
        sample_size=args.sample,
        verbose=not args.quiet,
    )
    
    # 保存报告
    if args.save:
        save_report(report)
    
    # 导出用户档案
    if args.export_users:
        data = generate_all_data()
        export_user_profiles(data["users"])
