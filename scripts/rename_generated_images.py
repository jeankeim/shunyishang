#!/usr/bin/env python3
"""
批量重命名已生成的图片文件（使用描述作为文件名）
"""

import os
import json
from pathlib import Path
from datetime import datetime


# 手动补充的 prompt 信息（按序号）
MANUAL_PROMPTS = {
    "001": "白色浅蓝色高支棉免烫衬衫",
    "002": "深棕色复古灯芯绒衬衫",
    "003": "炭灰色美利奴羊毛高领针织衫",
    "004": "纯白纯黑重磅纯棉圆领 T 恤",
    "005": "海军蓝意式休闲西装外套",
    "006": "深灰色 H 型羊毛混纺长款大衣",
}


def rename_existing_images():
    """重命名已有图片文件"""
    
    # 图片目录
    image_dir = Path(__file__).parent.parent / "data" / "generated_images" / "user_wardrobe"
    
    # 找到最新的日期目录
    date_dirs = [d for d in image_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    if not date_dirs:
        print("[ERROR] 未找到图片目录")
        return
    
    # 选择最新的日期目录
    latest_dir = max(date_dirs, key=lambda d: d.name)
    print(f"[INFO] 处理目录：{latest_dir}")
    
    # 读取所有 JSON 元数据文件
    json_files = list(latest_dir.glob("*.json"))
    
    renamed_count = 0
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            old_filename = metadata.get('filename', '')
            prompt = metadata.get('prompt', '')
            
            # 如果没有 prompt，尝试从文件名获取序号并查找手动补充的 prompt
            if not prompt:
                parts = old_filename.split("_")
                if len(parts) >= 2:
                    index = parts[1]  # 如 "001"
                    prompt = MANUAL_PROMPTS.get(index, '')
            
            if not old_filename:
                print(f"[SKIP] {json_file.name}: 缺少文件名")
                continue
            
            # 生成新文件名
            safe_prompt = prompt.replace("/", "_").replace("\\", "_")
            filename_base = safe_prompt[:30].strip()
            
            # 从旧文件名提取序号
            parts = old_filename.split("_")
            if len(parts) >= 2:
                index = parts[1]  # 如 "001"
                new_filename = f"image_{index}_{filename_base}.png"
            else:
                new_filename = f"image_{filename_base}.png"
            
            # 如果文件名相同，跳过
            if new_filename == old_filename:
                print(f"[SKIP] {old_filename}: 文件名无需更改")
                continue
            
            # 检查新文件名是否已存在
            new_path = latest_dir / new_filename
            old_path = latest_dir / old_filename
            
            if new_path.exists():
                print(f"[EXISTS] {new_filename}: 已存在")
                continue
            
            # 重命名文件
            if old_path.exists():
                old_path.rename(new_path)
                print(f"[OK] {old_filename} → {new_filename}")
                
                # 更新 JSON 中的 filename 和 prompt
                metadata['filename'] = new_filename
                if prompt:
                    metadata['prompt'] = prompt
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                renamed_count += 1
            else:
                print(f"[MISSING] {old_filename}: 文件不存在")
                
        except Exception as e:
            print(f"[ERROR] 处理 {json_file.name} 失败：{e}")
    
    print(f"\n[SUMMARY] 重命名完成：{renamed_count}/{len(json_files)} 个文件")


if __name__ == "__main__":
    rename_existing_images()
