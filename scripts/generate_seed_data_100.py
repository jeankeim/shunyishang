#!/usr/bin/env python3
"""
五行 AI 衣橱 - 基于种子数据自动生成多样化风格图片（100 件）

从 seed_data_100_enhanced.json 读取所有物品名称，生成无人物的多样化风格图片
"""

import json
from pathlib import Path
from typing import List, Dict
import random
import os
from datetime import datetime

# 复用主脚本的生成器
from generate_images import QwenImageGenerator, load_env_from_file


# ============================================================================
# 风格模板库（多样化和创意）
# ============================================================================

STYLE_TEMPLATES = [
    # 简约风格
    "极简主义风格，纯色背景，无模特，平铺拍摄",
    "北欧简约风，浅灰色背景，无模特，悬挂展示",
    "日式极简，米白色背景，无模特，精心摆放",
    
    # 专业摄影
    "商业产品摄影，渐变背景，无模特，专业灯光",
    "高端品牌画册风格，深色背景，无模特，戏剧性光影",
    "杂志大片风格，艺术背景，无模特，创意构图",
    
    # 自然风格
    "自然光拍摄，木质背景，无模特，生活化摆放",
    "ins 风，大理石纹理背景，无模特，精致摆拍",
    "清新田园风，亚麻布背景，无模特，自然褶皱",
    
    # 复古风格
    "复古胶片感，做旧背景，无模特，怀旧色调",
    "港风摄影，霓虹色背景，无模特，氛围感强",
    "美式复古，牛皮纸背景，无模特，粗犷质感",
    
    # 科技感
    "未来科技感，金属质感背景，无模特，冷色调",
    "赛博朋克风格，霓虹灯背景，无模特，炫酷光影",
    
    # 艺术风格
    "油画质感，艺术背景，无模特，古典美学",
    "水彩画风格，柔和背景，无模特，梦幻感",
    "抽象艺术，几何背景，无模特，现代感",
]


def get_style_for_item(item_name: str, index: int) -> str:
    """根据物品名称和索引选择合适的风格"""
    # 使用不同的随机种子确保风格多样性
    random.seed(hash(item_name) + index)
    return random.choice(STYLE_TEMPLATES)


def load_seed_data() -> List[Dict]:
    """加载种子数据"""
    seed_file = Path(__file__).parent.parent / "data" / "seeds" / "seed_data_100_enhanced.json"
    
    with open(seed_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def create_queries_from_seed(seed_data: List[Dict]) -> List[Dict]:
    """从种子数据创建查询列表"""
    queries = []
    
    for item in seed_data:
        item_name = item.get("物品名称", "")
        if not item_name:
            continue
        
        # 为每个物品搭配合适的风格
        style = get_style_for_item(item_name, len(queries))
        
        query = {
            "query": f"{item_name}，{style}",
            "category": item.get("分类", "未知"),
            "subcategory": item_name,
            "original_item_id": item.get("物品 ID", ""),
            "style": style
        }
        
        queries.append(query)
    
    return queries


def check_existing_files(output_dir: Path) -> set:
    """检查已生成的文件，返回已完成的物品名称集合"""
    existing = set()
    
    if not output_dir.exists():
        return existing
    
    # 读取所有 PNG 文件名
    for png_file in output_dir.glob("*.png"):
        filename = png_file.stem  # 不含扩展名
        # 从文件名提取物品名称（格式：image_序号_物品名称）
        parts = filename.split("_", 2)
        if len(parts) >= 3:
            item_name = parts[2]
            existing.add(item_name)
    
    return existing


def main():
    """主函数"""
    print("="*60)
    print("五行 AI 衣橱 - 种子数据批量图片生成（100 件）")
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
    
    # 加载种子数据
    print(f"\n[INFO] 正在读取种子数据...")
    seed_data = load_seed_data()
    print(f"[OK] 成功读取 {len(seed_data)} 个物品")
    
    # 创建查询列表
    queries = create_queries_from_seed(seed_data)
    print(f"[OK] 已创建 {len(queries)} 个查询")
    
    # 初始化生成器
    generator = QwenImageGenerator()
    
    # 自定义输出目录（种子数据）
    custom_output_dir = Path(__file__).parent.parent / "data" / "generated_images" / "seed_data_100"
    date_subdir = custom_output_dir / datetime.now().strftime("%Y%m%d")
    date_subdir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n[INFO] 将生成 {len(queries)} 张多样化风格衣物图片...")
    print(f"[INFO] 输出目录：{custom_output_dir}")
    
    # 检查已生成的文件
    print(f"\n[INFO] 检查已生成的文件...")
    existing_items = check_existing_files(date_subdir)
    print(f"[INFO] 已生成：{len(existing_items)} 个")
    
    if len(existing_items) >= len(queries):
        print(f"[SUCCESS] 所有 {len(queries)} 个物品已全部生成完成！")
        return
    
    # 过滤出未完成的物品
    remaining_queries = [q for q in queries if q["subcategory"] not in existing_items]
    print(f"[INFO] 待生成：{len(remaining_queries)} 个")
    
    # 按分类统计
    categories = {}
    for item in remaining_queries:
        cat = item["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\n[INFO] 待生成分类统计:")
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count} 件")
    
    # 批量生成
    print(f"\n[START] 开始批量生成剩余任务...")
    results = generator.generate_batch(
        queries=remaining_queries,
        output_dir=date_subdir,
        delay=2.5  # 2.5 秒间隔，避免限流
    )
    
    # 输出统计
    print(f"\n{'='*60}")
    print(f"[SUMMARY] 生成完成")
    print(f"{'='*60}")
    print(f"本次查询数：{len(remaining_queries)}")
    print(f"本次成功数：{len(results)}")
    print(f"本次失败数：{len(remaining_queries) - len(results)}")
    print(f"本次成功率：{len(results)/len(remaining_queries)*100:.1f}%")
    
    # 最终检查
    final_existing = check_existing_files(date_subdir)
    print(f"\n[FINAL CHECK]")
    print(f"总计已生成：{len(final_existing)}/{len(queries)} 个")
    
    if len(final_existing) < len(queries):
        missing = len(queries) - len(final_existing)
        print(f"[WARNING] 还有 {missing} 个未生成，将继续运行...")
        
        # 递归调用继续生成
        main()
        return
    
    print(f"\n[SUCCESS] 所有 {len(queries)} 个物品已全部生成完成！")
    print(f"\n输出目录：{custom_output_dir}")
    
    # 保存汇总报告
    report_path = custom_output_dir / f"generation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "total": len(queries),
            "success": len(final_existing),
            "failed": 0,
            "output_dir": str(custom_output_dir),
            "style": "多样化风格（无人物）",
            "styles_used": list(set(STYLE_TEMPLATES)),
            "completed_at": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n[INFO] 汇总报告已保存：{report_path}")
    print(f"\n[下一步]")
    print("1. 查看生成的图片：打开 data/generated_images/seed_data_100/ 目录")
    print("2. 检查质量：确认图片风格和多样性")
    print("3. 导入数据库：可将图片用于衣橱管理或推荐系统")


if __name__ == "__main__":
    main()
