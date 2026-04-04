#!/usr/bin/env python3
"""
图片上传功能 - 分步调试脚本
逐步验证图片从上传到显示的完整流程
"""

import requests
import json

API_BASE = "http://localhost:8000"

def step1_login():
    """Step 1: 登录获取 Token"""
    print("\n" + "="*60)
    print("Step 1: 用户登录")
    print("="*60)
    
    login_data = {
        "username": "test@example.com",
        "password": "Test123456"
    }
    
    response = requests.post(f"{API_BASE}/api/v1/auth/login", data=login_data)
    
    if response.ok:
        token = response.json()["access_token"]
        user_id = response.json().get("user", {}).get("id")
        print(f"✅ 登录成功")
        print(f"   用户 ID: {user_id}")
        print(f"   Token: {token[:50]}...")
        return token, user_id
    else:
        print(f"❌ 登录失败：{response.status_code}")
        return None, None


def step2_upload_image(token):
    """Step 2: 上传图片"""
    print("\n" + "="*60)
    print("Step 2: 上传图片")
    print("="*60)
    
    if not token:
        print("❌ 跳过：没有 token")
        return None
    
    # 创建测试图片（1x1 PNG）
    test_image = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0xF0,
        0x00, 0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05,
        0xFE, 0xD4, 0xEF, 0x00, 0x00, 0x00, 0x00, 0x49,
        0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    
    files = {"file": ("debug_test.png", test_image, "image/png")}
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(
        f"{API_BASE}/api/v1/wardrobe/upload-image",
        headers=headers,
        files=files
    )
    
    if response.ok:
        result = response.json()
        image_url = result["image_url"]
        print(f"✅ 上传成功")
        print(f"   返回 URL: {image_url}")
        
        # 验证文件是否真的保存了
        import os
        from pathlib import Path
        file_path = Path(__file__).parent / "data" / "uploads" / "wardrobe"
        print(f"   存储目录：{file_path}")
        
        if file_path.exists():
            files_in_dir = list(file_path.glob("**/*"))
            print(f"   目录内容：{[str(f) for f in files_in_dir[:10]]}")
        
        return image_url
    else:
        print(f"❌ 上传失败：{response.status_code}")
        print(f"   错误信息：{response.text}")
        return None


def step3_verify_static_file(image_url):
    """Step 3: 验证静态文件可访问"""
    print("\n" + "="*60)
    print("Step 3: 验证静态文件服务")
    print("="*60)
    
    if not image_url:
        print("❌ 跳过：没有图片 URL")
        return False
    
    full_url = f"{API_BASE}{image_url}"
    print(f"   访问 URL: {full_url}")
    
    response = requests.get(full_url)
    
    if response.ok:
        print(f"✅ 图片可访问")
        print(f"   状态码：{response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   文件大小：{len(response.content)} bytes")
        return True
    else:
        print(f"❌ 图片访问失败")
        print(f"   状态码：{response.status_code}")
        print(f"   响应内容：{response.text[:200]}")
        return False


def step4_add_wardrobe_item(token, image_url):
    """Step 4: 添加衣物到衣橱"""
    print("\n" + "="*60)
    print("Step 4: 添加衣物（包含图片 URL）")
    print("="*60)
    
    if not token or not image_url:
        print("❌ 跳过：缺少必要参数")
        return None
    
    payload = {
        "name": "调试测试衬衫",
        "category": "上装",
        "image_url": image_url,  # ← 关键：确保这个字段正确传递
        "primary_element": "金",
        "secondary_element": None,
        "description": "用于调试图片显示问题",
        "attributes_detail": {
            "颜色": {
                "名称": "白色",
                "主五行": "金"
            },
            "面料": {
                "名称": "棉质",
                "主五行": "木"
            },
            "款式": {
                "形状": "长方",
                "细节": [],
                "风格": "休闲"
            },
            "season": ["春", "秋"],
            "tags": ["测试", "调试"]
        },
        "gender": "男女通用",
        "applicable_weather": ["晴", "多云"],
        "applicable_seasons": ["春", "秋"],
        "thickness_level": "适中"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"   请求数据:")
    print(f"   - name: {payload['name']}")
    print(f"   - category: {payload['category']}")
    print(f"   - image_url: {payload['image_url']}")
    print(f"   - primary_element: {payload['primary_element']}")
    
    response = requests.post(
        f"{API_BASE}/api/v1/wardrobe/items",
        headers=headers,
        json=payload
    )
    
    if response.ok:
        item = response.json()
        print(f"✅ 添加成功")
        print(f"   衣物 ID: {item['id']}")
        print(f"   名称：{item['name']}")
        print(f"   保存的 image_url: {item['image_url']}")
        
        # 验证 image_url 是否正确保存
        if item['image_url'] == image_url:
            print(f"   ✅ image_url 正确保存")
        else:
            print(f"   ⚠️  image_url 不一致！")
            print(f"      原始：{image_url}")
            print(f"      保存：{item['image_url']}")
        
        return item
    else:
        print(f"❌ 添加失败：{response.status_code}")
        print(f"   错误信息：{response.text}")
        return None


def step5_get_wardrobe_list(token):
    """Step 5: 获取衣橱列表"""
    print("\n" + "="*60)
    print("Step 5: 获取衣橱列表")
    print("="*60)
    
    if not token:
        print("❌ 跳过：没有 token")
        return []
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/api/v1/wardrobe/items",
        headers=headers,
        params={"limit": 10}
    )
    
    if response.ok:
        data = response.json()
        total = data["total"]
        items = data["items"]
        
        print(f"✅ 获取成功")
        print(f"   总数：{total}")
        print(f"   返回数量：{len(items)}")
        
        if items:
            print(f"\n   最新衣物:")
            for i, item in enumerate(items[:3], 1):
                print(f"   [{i}] ID:{item['id']} - {item['name']}")
                print(f"       image_url: {item.get('image_url', 'N/A')}")
                
                # 检查 image_url 字段
                has_image = bool(item.get('image_url'))
                print(f"       {'✅' if has_image else '❌'} image_url 字段{'存在' if has_image else '缺失'}")
        else:
            print(f"   ⚠️  衣橱为空")
        
        return items
    else:
        print(f"❌ 获取失败：{response.status_code}")
        print(f"   错误信息：{response.text}")
        return []


def step6_verify_image_in_list(items):
    """Step 6: 验证列表中的图片"""
    print("\n" + "="*60)
    print("Step 6: 验证衣橱列表中的图片")
    print("="*60)
    
    if not items:
        print("❌ 跳过：没有衣物数据")
        return False
    
    # 查找刚添加的衣物
    test_item = None
    for item in items:
        if "调试" in item['name'] or "测试" in item['name']:
            test_item = item
            break
    
    if not test_item:
        test_item = items[0]
    
    print(f"   检查衣物：{test_item['name']} (ID: {test_item['id']})")
    
    image_url = test_item.get('image_url')
    
    if not image_url:
        print(f"❌ image_url 字段缺失")
        return False
    
    print(f"   image_url: {image_url}")
    
    # 尝试访问图片
    full_url = f"{API_BASE}{image_url}"
    try:
        img_response = requests.get(full_url)
        
        if img_response.ok:
            print(f"✅ 图片可访问")
            print(f"   URL: {full_url}")
            print(f"   状态码：{img_response.status_code}")
            print(f"   Content-Type: {img_response.headers.get('Content-Type')}")
            print(f"   大小：{len(img_response.content)} bytes")
            return True
        else:
            print(f"❌ 图片访问失败")
            print(f"   URL: {full_url}")
            print(f"   状态码：{img_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 访问异常：{e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🔍 图片上传功能 - 分步调试")
    print("="*60)
    
    # Step 1: 登录
    token, user_id = step1_login()
    if not token:
        print("\n❌ 测试终止：登录失败")
        return
    
    # Step 2: 上传图片
    image_url = step2_upload_image(token)
    if not image_url:
        print("\n❌ 测试终止：图片上传失败")
        return
    
    # Step 3: 验证静态文件
    static_ok = step3_verify_static_file(image_url)
    if not static_ok:
        print("\n❌ 测试终止：静态文件不可访问")
        return
    
    # Step 4: 添加衣物
    added_item = step4_add_wardrobe_item(token, image_url)
    if not added_item:
        print("\n❌ 测试终止：添加衣物失败")
        return
    
    # Step 5: 获取衣橱列表
    items = step5_get_wardrobe_list(token)
    if not items:
        print("\n❌ 测试终止：获取衣橱列表失败")
        return
    
    # Step 6: 验证图片
    image_ok = step6_verify_image_in_list(items)
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    if image_ok:
        print("✅ 所有步骤通过！后端功能正常")
        print("\n✨ 验证结果:")
        print("  ✓ 用户登录正常")
        print("  ✓ 图片上传成功")
        print("  ✓ JWT 认证生效")
        print("  ✓ 衣物添加成功")
        print("  ✓ image_url 保存正确")
        print("  ✓ 衣橱列表返回数据")
        print("  ✓ 图片可正常访问")
        print("\n🎉 后端功能完全正常！")
        print("\n💡 如果前端仍然无法显示，问题可能在于:")
        print("  1. 前端组件没有正确接收 imageUrl")
        print("  2. displayImage 计算逻辑有问题")
        print("  3. 图片渲染条件判断有误")
        print("  4. 需要检查前端控制台错误")
    else:
        print("⚠️  部分测试失败")
        print("\n需要检查:")
        print("  1. 后端服务日志：logs/backend.log")
        print("  2. 静态文件配置：apps/api/main.py")
        print("  3. 数据库连接状态")
        print("  4. 文件权限设置")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
