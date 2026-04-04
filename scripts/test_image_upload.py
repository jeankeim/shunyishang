#!/usr/bin/env python3
"""
Week 5 任务 1: 图片上传功能 - 端到端测试脚本

测试流程:
1. 用户登录
2. 上传图片
3. 添加衣物（包含图片 URL）
4. 获取衣橱列表
5. 验证图片显示
6. 访问图片 URL

使用方法:
python scripts/test_image_upload.py
"""

import requests
import json
import sys
from pathlib import Path

# API 基础 URL
API_BASE = "http://localhost:8000"

def create_test_image():
    """创建一个简单的测试图片（1x1 PNG）"""
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG header
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0xF0,
        0x00, 0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05,
        0xFE, 0xD4, 0xEF, 0x00, 0x00, 0x00, 0x00, 0x49,
        0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
    ])


def test_login():
    """测试 1: 用户登录"""
    print("\n" + "="*60)
    print("📝 测试 1: 用户登录")
    print("="*60)
    
    login_data = {
        "username": "test@example.com",
        "password": "Test123456"
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/v1/auth/login", data=login_data)
        
        if response.status_code == 401:
            print("⚠️  测试账号不存在，尝试注册...")
            # 注册新账号
            register_data = {
                "email": "test@example.com",
                "password": "Test123456",
                "nickname": "测试用户"
            }
            response = requests.post(f"{API_BASE}/api/v1/auth/register", json=register_data)
            if response.ok:
                print("✅ 注册成功")
                # 重新登录
                response = requests.post(f"{API_BASE}/api/v1/auth/login", data=login_data)
        
        if response.ok:
            token = response.json()["access_token"]
            user = response.json().get("user", {})
            print(f"✅ 登录成功")
            print(f"👤 用户 ID: {user.get('id', 'N/A')}")
            print(f"🔑 Token: {token[:50]}...")
            return token
        else:
            print(f"❌ 登录失败：{response.status_code}")
            print(f"错误信息：{response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 登录异常：{e}")
        return None


def test_image_upload(token):
    """测试 2: 上传图片"""
    print("\n" + "="*60)
    print("📤 测试 2: 上传图片")
    print("="*60)
    
    if not token:
        print("❌ 跳过：未获取到 token")
        return None
    
    test_image = create_test_image()
    files = {"file": ("test_shirt.png", test_image, "image/png")}
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/wardrobe/upload-image",
            headers=headers,
            files=files
        )
        
        if response.ok:
            result = response.json()
            image_url = result["image_url"]
            print(f"✅ 上传成功")
            print(f"📄 返回 URL: {image_url}")
            
            # 验证图片可访问性
            full_url = f"{API_BASE}{image_url}"
            img_response = requests.get(full_url)
            if img_response.ok:
                print(f"✅ 图片可访问：{full_url}")
                print(f"📊 图片大小：{len(img_response.content)} bytes")
                print(f"📦 Content-Type: {img_response.headers.get('Content-Type')}")
                return image_url
            else:
                print(f"❌ 图片访问失败：{img_response.status_code}")
                return None
        else:
            print(f"❌ 上传失败：{response.status_code}")
            print(f"错误信息：{response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 上传异常：{e}")
        return None


def test_add_wardrobe_item(token, image_url):
    """测试 3: 添加衣物到衣橱"""
    print("\n" + "="*60)
    print("👕 测试 3: 添加衣物到衣橱")
    print("="*60)
    
    if not token or not image_url:
        print("❌ 跳过：缺少必要参数")
        return None
    
    payload = {
        "name": "测试衬衫",
        "category": "上装",
        "image_url": image_url,
        "primary_element": "金",
        "secondary_element": None,
        "description": "这是一件测试用的衬衫",
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
            "tags": ["衬衫", "白色", "休闲"]
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
    
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/wardrobe/items",
            headers=headers,
            json=payload
        )
        
        if response.ok:
            item = response.json()
            print(f"✅ 添加成功")
            print(f"📄 衣物 ID: {item['id']}")
            print(f"🏷️  名称：{item['name']}")
            print(f"📂 分类：{item['category']}")
            print(f"🎨 五行：{item['primary_element']}")
            print(f"🖼️  图片 URL: {item['image_url']}")
            return item
        else:
            print(f"❌ 添加失败：{response.status_code}")
            print(f"错误信息：{response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 添加异常：{e}")
        return None


def test_get_wardrobe_list(token):
    """测试 4: 获取衣橱列表"""
    print("\n" + "="*60)
    print("📋 测试 4: 获取衣橱列表")
    print("="*60)
    
    if not token:
        print("❌ 跳过：未获取到 token")
        return []
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
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
            print(f"📊 总数：{total}")
            print(f"📦 返回数量：{len(items)}")
            
            if items:
                print(f"\n📄 最新衣物:")
                item = items[0]
                print(f"  - ID: {item['id']}")
                print(f"  - 名称：{item['name']}")
                print(f"  - 分类：{item['category']}")
                print(f"  - 五行：{item['primary_element']}")
                print(f"  - 图片 URL: {item.get('image_url', 'N/A')}")
                
                # 检查 image_url
                if not item.get('image_url'):
                    print(f"\n⚠️  WARNING: image_url 为空！")
                else:
                    print(f"\n✅ image_url 存在")
            
            return items
        else:
            print(f"❌ 获取失败：{response.status_code}")
            print(f"错误信息：{response.text}")
            return []
            
    except Exception as e:
        print(f"❌ 获取异常：{e}")
        return []


def verify_image_display(items):
    """测试 5: 验证图片显示"""
    print("\n" + "="*60)
    print("🖼️  测试 5: 验证图片显示")
    print("="*60)
    
    if not items:
        print("❌ 跳过：没有衣物数据")
        return False
    
    # 查找有图片的衣物
    items_with_images = [item for item in items if item.get('image_url')]
    
    if not items_with_images:
        print("⚠️  没有找到带图片的衣物")
        return False
    
    print(f"✅ 找到 {len(items_with_images)} 件带图片的衣物")
    
    # 测试第一件衣物的图片
    item = items_with_images[0]
    image_url = item['image_url']
    
    print(f"\n📄 测试衣物：{item['name']}")
    print(f"🔗 图片 URL: {image_url}")
    
    # 验证图片可访问性
    try:
        full_url = f"{API_BASE}{image_url}"
        img_response = requests.get(full_url)
        
        if img_response.ok:
            print(f"✅ 图片可访问")
            print(f"📊 图片大小：{len(img_response.content)} bytes")
            print(f"📦 Content-Type: {img_response.headers.get('Content-Type')}")
            return True
        else:
            print(f"❌ 图片访问失败：{img_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 验证异常：{e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🧪 Week 5 任务 1: 图片上传功能 - 端到端测试")
    print("="*60)
    
    # Step 1: 登录
    token = test_login()
    if not token:
        print("\n❌ 测试终止：登录失败")
        sys.exit(1)
    
    # Step 2: 上传图片
    image_url = test_image_upload(token)
    if not image_url:
        print("\n❌ 测试终止：图片上传失败")
        sys.exit(1)
    
    # Step 3: 添加衣物
    added_item = test_add_wardrobe_item(token, image_url)
    if not added_item:
        print("\n❌ 测试终止：添加衣物失败")
        sys.exit(1)
    
    # Step 4: 获取衣橱列表
    items = test_get_wardrobe_list(token)
    if not items:
        print("\n❌ 测试终止：获取衣橱列表失败")
        sys.exit(1)
    
    # Step 5: 验证图片显示
    success = verify_image_display(items)
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    if success:
        print("✅ 所有测试通过！")
        print("\n✨ 功能验证:")
        print("  ✓ 用户登录正常")
        print("  ✓ 图片上传成功")
        print("  ✓ JWT 认证生效")
        print("  ✓ 衣物添加成功")
        print("  ✓ 图片 URL 保存正确")
        print("  ✓ 衣橱列表显示正常")
        print("  ✓ 图片可访问")
        print("\n🎉 图片上传功能完全正常！")
        sys.exit(0)
    else:
        print("⚠️  部分测试失败")
        print("\n需要检查:")
        print("  1. 后端服务是否正常运行")
        print("  2. 静态文件服务是否正确配置")
        print("  3. 数据库连接是否正常")
        print("  4. 查看后端日志：logs/backend.log")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
