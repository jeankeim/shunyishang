#!/usr/bin/env python3
"""
批量添加优衣库风格图片到衣橱
使用方式: python scripts/batch_add_to_wardrobe.py
"""

import os
import sys
import re
import json
import requests
from pathlib import Path
from typing import List, Tuple

# 配置
BASE_URL = "http://localhost:8000"
IMAGE_DIRS = [
    "data/generated_images/uniqlo_style/20260401",
    "data/generated_images/uniqlo_style_batch2/20260401"
]
USER_ID = 1  # 默认用户ID

# 从环境变量或配置文件读取token
TOKEN = os.getenv("API_TOKEN", "")

def extract_description(filename: str) -> str:
    """
    从文件名提取描述
    例如: image_001_白色高支棉免烫衬衫，简约设计，纯色背景，无模特，平铺拍摄.png
    提取: 白色高支棉免烫衬衫
    """
    # 移除扩展名
    name_without_ext = Path(filename).stem
    
    # 匹配 image_XXX_描述_其他信息 的模式
    # 提取第一个逗号前的内容作为描述
    match = re.match(r'image_\d+_(.+?)[，,_]', name_without_ext)
    if match:
        return match.group(1)
    
    # 如果没有匹配到，返回文件名（不含序号）
    parts = name_without_ext.split('_', 2)
    if len(parts) >= 3:
        return parts[2]
    
    return name_without_ext

def get_image_files() -> List[Tuple[str, str]]:
    """获取所有图片文件路径和描述"""
    images = []
    base_path = Path(__file__).parent.parent
    
    for dir_path in IMAGE_DIRS:
        full_path = base_path / dir_path
        if not full_path.exists():
            print(f"⚠️ 目录不存在: {full_path}")
            continue
        
        # 获取所有png文件
        for png_file in sorted(full_path.glob("*.png")):
            description = extract_description(png_file.name)
            images.append((str(png_file), description))
    
    return images

def login_and_get_token() -> str:
    """登录获取token"""
    print("🔐 正在登录获取token...")
    
    # 尝试使用 18510721913 账号登录 (FastAPI OAuth2 格式)
    login_data = {
        "username": "18510721913",
        "password": "frank230"
    }
    
    try:
        # 使用 form-data 格式
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            data=login_data  # 使用 data 而不是 json
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✅ 登录成功")
            return token
        else:
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return ""

def upload_image(image_path: str, token: str) -> str:
    """上传图片到服务器"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        with open(image_path, "rb") as f:
            files = {"file": (Path(image_path).name, f, "image/png")}
            response = requests.post(
                f"{BASE_URL}/api/v1/wardrobe/upload-image",
                headers=headers,
                files=files
            )
        
        if response.status_code == 200:
            image_url = response.json().get("image_url")
            print(f"  ✅ 图片上传成功: {image_url}")
            return image_url
        else:
            print(f"  ❌ 图片上传失败: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        print(f"  ❌ 图片上传异常: {e}")
        return ""

def ai_analyze(description: str, image_url: str, token: str) -> dict:
    """调用AI分析接口"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "description": description,
        "image_url": image_url
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/wardrobe/items/preview-tagging",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ AI分析完成: {result.get('suggested_name', 'N/A')}")
            return result
        else:
            print(f"  ❌ AI分析失败: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        print(f"  ❌ AI分析异常: {e}")
        return {}

def add_to_wardrobe(analysis: dict, description: str, image_url: str, token: str) -> bool:
    """添加衣物到衣橱"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 构建请求数据
    data = {
        "name": description,
        "category": analysis.get("category", "上衣"),
        "image_url": image_url,
        "primary_element": analysis.get("primary_element", "金"),
        "secondary_element": analysis.get("secondary_element"),
        "description": description,
        "applicable_weather": analysis.get("applicable_weather", []),
        "applicable_seasons": analysis.get("applicable_seasons", []),
        "temperature_range": analysis.get("temperature_range"),
        "functionality": analysis.get("functionality", []),
        "thickness_level": analysis.get("thickness_level"),
        "energy_intensity": analysis.get("energy_intensity"),
        "attributes_detail": {
            "颜色": {
                "名称": analysis.get("color", ""),
                "主五行": analysis.get("color_element", "")
            },
            "面料": {
                "名称": analysis.get("material", ""),
                "主五行": analysis.get("material_element", "")
            },
            "款式": {
                "形状": analysis.get("shape", ""),
                "细节": analysis.get("details", []),
                "风格": analysis.get("style", "")
            },
            "season": analysis.get("season", []),
            "tags": analysis.get("tags", [])
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/wardrobe/items",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            print(f"  ✅ 成功添加到衣橱")
            return True
        else:
            print(f"  ❌ 添加到衣橱失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ 添加到衣橱异常: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 开始批量添加衣物到衣橱")
    print("=" * 60)
    
    # 获取token
    token = TOKEN or login_and_get_token()
    if not token:
        print("❌ 无法获取token，请检查登录信息")
        sys.exit(1)
    
    # 获取所有图片
    images = get_image_files()
    print(f"\n📸 找到 {len(images)} 张图片")
    print("-" * 60)
    
    # 统计
    success_count = 0
    fail_count = 0
    
    # 处理每张图片
    for idx, (image_path, description) in enumerate(images, 1):
        print(f"\n[{idx}/{len(images)}] 处理: {Path(image_path).name}")
        print(f"  描述: {description}")
        
        # 1. 上传图片
        image_url = upload_image(image_path, token)
        if not image_url:
            fail_count += 1
            continue
        
        # 2. AI分析
        analysis = ai_analyze(description, image_url, token)
        if not analysis:
            fail_count += 1
            continue
        
        # 3. 添加到衣橱
        if add_to_wardrobe(analysis, description, image_url, token):
            success_count += 1
        else:
            fail_count += 1
    
    # 统计结果
    print("\n" + "=" * 60)
    print("📊 批量添加完成")
    print(f"  ✅ 成功: {success_count}")
    print(f"  ❌ 失败: {fail_count}")
    print(f"  📈 总计: {len(images)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
