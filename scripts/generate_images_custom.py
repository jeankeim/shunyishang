#!/usr/bin/env python3
"""
五行 AI 衣橱 - 自定义图片生成示例

演示如何使用 QwenImageGenerator 生成特定衣物图片

Usage:
    python generate_images_custom.py
"""

import os
from pathlib import Path

# 复用主脚本的生成器
from generate_images import QwenImageGenerator, load_env_from_file, create_output_directory


# ============================================================================
# 自定义查询示例
# ============================================================================

CUSTOM_QUERIES = [
    # 示例 1: 按五行属性生成
    {
        "query": "一件绿色棉麻衬衫，宽松版型，自然风格，适合春天穿着",
        "category": "上装",
        "element": "木",
        "season": "春"
    },
    {
        "query": "红色真丝吊带裙，修身剪裁，性感风格，夏季晚宴穿搭",
        "category": "裙装",
        "element": "火",
        "season": "夏"
    },
    {
        "query": "黄色羊毛针织开衫，V 领设计，温柔气质，秋季日常",
        "category": "上装",
        "element": "土",
        "season": "秋"
    },
    {
        "query": "白色高领毛衣，粗针编织，温暖感觉，冬季保暖",
        "category": "上装",
        "element": "金",
        "season": "冬"
    },
    {
        "query": "黑色皮质夹克，机车风格，拉链装饰，酷帅街头",
        "category": "外套",
        "element": "水",
        "season": "春秋"
    },
    
    # 示例 2: 按场景生成
    {
        "query": "商务正装套装，深灰色，精致剪裁，职场通勤，专业干练",
        "category": "套装",
        "scenario": "通勤"
    },
    {
        "query": "运动休闲卫衣，连帽设计，舒适面料，周末出游，轻松自在",
        "category": "上装",
        "scenario": "休闲"
    },
    {
        "query": "优雅晚礼服，长款，蕾丝装饰，宴会场合，高贵典雅",
        "category": "裙装",
        "scenario": "宴会"
    },
    {
        "query": "户外冲锋衣，防水透气，多功能口袋，登山徒步，专业装备",
        "category": "外套",
        "scenario": "户外"
    },
    
    # 示例 3: 按风格生成
    {
        "query": "法式复古连衣裙，碎花图案，泡泡袖，浪漫田园风",
        "category": "裙装",
        "style": "复古"
    },
    {
        "query": "日式极简风衣，素色，宽松廓形，性冷淡风，高级感",
        "category": "外套",
        "style": "极简"
    },
    {
        "query": "美式街头潮牌 T 恤，oversize 版型，印花图案，嘻哈风格",
        "category": "上装",
        "style": "街头"
    },
]


def main():
    """主函数"""
    print("="*60)
    print("五行 AI 衣橱 - 自定义图片生成")
    print("="*60)
    
    # 加载环境变量
    load_env_from_file()
    
    # 创建输出目录
    create_output_directory()
    
    # 初始化生成器
    generator = QwenImageGenerator()
    
    # 自定义输出目录（带标签）
    custom_output_dir = Path(__file__).parent.parent / "data" / "generated_images" / "custom"
    custom_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[INFO] 将生成 {len(CUSTOM_QUERIES)} 张自定义图片...")
    print(f"[INFO] 输出目录：{custom_output_dir}")
    
    # 批量生成
    results = generator.generate_batch(
        queries=CUSTOM_QUERIES,
        output_dir=custom_output_dir,
        delay=2.0
    )
    
    # 输出统计
    print(f"\n{'='*60}")
    print(f"[SUMMARY] 自定义生成完成")
    print(f"{'='*60}")
    print(f"成功：{len(results)}/{len(CUSTOM_QUERIES)}")
    print(f"输出目录：{custom_output_dir}")


if __name__ == "__main__":
    main()
