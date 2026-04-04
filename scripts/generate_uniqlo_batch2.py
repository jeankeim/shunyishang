#!/usr/bin/env python3
"""
五行 AI 衣橱 - 优衣库风格批量图片生成（第二批）

继续生成剩余的 22 件衣物图片
"""

import os
from pathlib import Path
from typing import List, Dict

# 复用主脚本的生成器
from generate_images import QwenImageGenerator, load_env_from_file, create_output_directory


# ============================================================================
# 待生成的 Query 列表（第二批）
# ============================================================================

REMAINING_QUERIES = [
    # ========== 上装类 ==========
    {
        "query": "藏青色珠地棉 POLO 衫，夏季职场，纯色背景，无模特，平铺拍摄",
        "category": "上装",
        "subcategory": "POLO 衫"
    },
    {
        "query": "深灰色纯棉加绒连帽卫衣，休闲保暖，纯色背景，无模特，平铺拍摄",
        "category": "上装",
        "subcategory": "卫衣"
    },
    {
        "query": "黑色哑光面料翻领短款羽绒服，冬季保暖，纯色背景，无模特，悬挂拍摄",
        "category": "外套",
        "subcategory": "羽绒服"
    },
    {
        "query": "黑色立领行政夹克，职场万能，纯色背景，无模特，悬挂拍摄",
        "category": "外套",
        "subcategory": "夹克"
    },
    {
        "query": "卡其色多口袋工装马甲，Cityboy 风格，纯色背景，无模特，平铺拍摄",
        "category": "外套",
        "subcategory": "马甲"
    },
    
    # ========== 下装类 ==========
    {
        "query": "原色直筒微弹牛仔裤，修饰腿型，纯色背景，无模特，平铺拍摄",
        "category": "下装",
        "subcategory": "牛仔裤"
    },
    {
        "query": "深灰色垂感抗皱休闲西裤，面料垂顺，纯色背景，无模特，平铺拍摄",
        "category": "下装",
        "subcategory": "西裤"
    },
    {
        "query": "焦糖色宽条纹灯芯绒休闲裤，复古温暖，纯色背景，无模特，平铺拍摄",
        "category": "下装",
        "subcategory": "休闲裤"
    },
    {
        "query": "军绿色多口袋束脚工装裤，硬朗机能风，纯色背景，无模特，平铺拍摄",
        "category": "下装",
        "subcategory": "工装裤"
    },
    {
        "query": "浅卡其色五分百慕大西裤，夏季清爽，纯色背景，无模特，平铺拍摄",
        "category": "下装",
        "subcategory": "短裤"
    },
    
    # ========== 鞋履与配饰 ==========
    {
        "query": "黑色哑光皮切尔西靴，一脚蹬设计，纯色背景，无模特，静物拍摄",
        "category": "鞋履",
        "subcategory": "靴子"
    },
    {
        "query": "纯白皮质板鞋，百搭休闲，纯色背景，无模特，静物拍摄",
        "category": "鞋履",
        "subcategory": "运动鞋"
    },
    {
        "query": "深棕色拼接皮质休闲运动鞋，运动休闲风，纯色背景，无模特，静物拍摄",
        "category": "鞋履",
        "subcategory": "运动鞋"
    },
    {
        "query": "黑色针扣牛皮皮带，经典款式，纯色背景，无模特，卷曲摆放",
        "category": "配饰",
        "subcategory": "皮带"
    },
    {
        "query": "棕色针扣牛皮皮带，经典款式，纯色背景，无模特，卷曲摆放",
        "category": "配饰",
        "subcategory": "皮带"
    },
    {
        "query": "银色表盘钢带机械腕表，简约大气，纯色背景，无模特，静物拍摄",
        "category": "配饰",
        "subcategory": "腕表"
    },
    {
        "query": "黑色尼龙材质简约双肩包，防水实用，纯色背景，无模特，静物拍摄",
        "category": "配饰",
        "subcategory": "包袋"
    },
    {
        "query": "蓝白格纹纯棉法兰绒衬衫，周末休闲，纯色背景，无模特，平铺拍摄",
        "category": "上装",
        "subcategory": "衬衫"
    },
    {
        "query": "深灰色法兰绒加绒西裤，秋冬厚实，纯色背景，无模特，平铺拍摄",
        "category": "下装",
        "subcategory": "西裤"
    },
    {
        "query": "沙色修身直筒斜纹棉布裤，春夏清爽，纯色背景，无模特，平铺拍摄",
        "category": "下装",
        "subcategory": "休闲裤"
    },
    {
        "query": "深驼色双面呢羊毛大衣，H 型设计，纯色背景，无模特，悬挂拍摄",
        "category": "外套",
        "subcategory": "大衣"
    },
    {
        "query": "浅灰色圆领美利奴羊毛衫，轻薄舒适，纯色背景，无模特，平铺拍摄",
        "category": "上装",
        "subcategory": "针织衫"
    },
    {
        "query": "深蓝色 V 领羊绒针织衫，质感细腻，纯色背景，无模特，平铺拍摄",
        "category": "上装",
        "subcategory": "针织衫"
    },
    {
        "query": "棕色牛津皮德比鞋，温润自然，纯色背景，无模特，静物拍摄",
        "category": "鞋履",
        "subcategory": "皮鞋"
    },
]


def main():
    """主函数"""
    print("="*60)
    print("五行 AI 衣橱 - 优衣库风格批量图片生成（第二批）")
    print("="*60)
    
    # 从.env 文件加载环境变量
    load_env_from_file()
    
    # 确保 API Key 已加载
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("[ERROR] 未找到 DASHSCOPE_API_KEY")
        print("[INFO] 请检查 .env 文件配置")
        return
    
    print(f"[OK] API Key 已加载 ({len(api_key)} 字符)")
    
    # 创建输出目录
    create_output_directory()
    
    # 初始化生成器
    generator = QwenImageGenerator()
    
    # 自定义输出目录（第二批）
    custom_output_dir = Path(__file__).parent.parent / "data" / "generated_images" / "uniqlo_style_batch2"
    custom_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[INFO] 将生成 {len(REMAINING_QUERIES)} 张优衣库风格衣物图片...")
    print(f"[INFO] 输出目录：{custom_output_dir}")
    print(f"[INFO] 分类统计:")
    
    # 按分类统计
    categories = {}
    for item in REMAINING_QUERIES:
        cat = item["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count} 件")
    
    # 批量生成
    print(f"\n[START] 开始批量生成...")
    results = generator.generate_batch(
        queries=REMAINING_QUERIES,
        output_dir=custom_output_dir,
        delay=2.5  # 2.5 秒间隔，避免限流
    )
    
    # 输出统计
    print(f"\n{'='*60}")
    print(f"[SUMMARY] 生成完成")
    print(f"{'='*60}")
    print(f"总查询数：{len(REMAINING_QUERIES)}")
    print(f"成功数：{len(results)}")
    print(f"失败数：{len(REMAINING_QUERIES) - len(results)}")
    print(f"成功率：{len(results)/len(REMAINING_QUERIES)*100:.1f}%")
    print(f"\n输出目录：{custom_output_dir}")
    
    # 保存汇总报告
    from datetime import datetime
    report_path = custom_output_dir / f"generation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    import json
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(REMAINING_QUERIES),
            "success": len(results),
            "failed": len(REMAINING_QUERIES) - len(results),
            "categories": categories,
            "results": results,
            "output_dir": str(custom_output_dir),
            "style": "优衣库简约风格（无人物）- 第二批"
        }, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n[INFO] 汇总报告已保存：{report_path}")
    print(f"\n[下一步]")
    print("1. 查看生成的图片：打开 data/generated_images/uniqlo_style_batch2/ 目录")
    print("2. 检查质量：确认图片是否符合优衣库简约风格")
    print("3. 导入数据库：可将图片用于衣橱管理或推荐系统")


if __name__ == "__main__":
    main()
