#!/usr/bin/env python3
"""
删除其他用户的衣橱衣物，只保留指定用户的衣物
使用方式: python scripts/cleanup_other_users_wardrobe.py
"""

import os
import sys
import requests
from pathlib import Path
import shutil

# 配置
BASE_URL = "http://localhost:8000"
KEEP_USER_ID = 1  # 保留的用户ID (18510721913)
DELETE_USER_IDS = [2, 3]  # 要删除的用户ID

def login_and_get_token() -> str:
    """登录获取token"""
    print("🔐 正在登录获取token...")
    
    login_data = {
        "username": "18510721913",
        "password": "frank230"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            data=login_data
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

def get_user_wardrobe_items(user_id: int, token: str) -> list:
    """获取用户的衣橱物品列表"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 注意：这里需要管理员权限或特定接口
        # 暂时通过直接查询数据库的方式
        return []
    except Exception as e:
        print(f"❌ 获取用户 {user_id} 衣橱失败: {e}")
        return []

def delete_wardrobe_item(item_id: int, token: str) -> bool:
    """删除衣橱物品"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.delete(
            f"{BASE_URL}/api/v1/wardrobe/items/{item_id}",
            headers=headers
        )
        if response.status_code == 200:
            return True
        else:
            print(f"  ❌ 删除失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ 删除异常: {e}")
        return False

def delete_user_files(user_id: int):
    """删除用户的文件"""
    user_dir = Path(f"/Users/mingyang/Desktop/shunyishang/data/uploads/wardrobe/{user_id}")
    
    if not user_dir.exists():
        print(f"  ℹ️ 用户 {user_id} 的文件目录不存在")
        return 0
    
    try:
        # 统计文件数量
        files = list(user_dir.glob("*"))
        file_count = len(files)
        
        # 删除整个目录
        shutil.rmtree(user_dir)
        print(f"  ✅ 已删除用户 {user_id} 的文件目录 ({file_count} 个文件)")
        return file_count
    except Exception as e:
        print(f"  ❌ 删除用户 {user_id} 文件失败: {e}")
        return 0

def main():
    print("=" * 60)
    print("🧹 开始清理其他用户的衣橱")
    print(f"📌 保留用户ID: {KEEP_USER_ID} (18510721913)")
    print(f"🗑️  删除用户ID: {DELETE_USER_IDS}")
    print("=" * 60)
    
    # 获取token
    token = login_and_get_token()
    if not token:
        print("❌ 无法获取token")
        sys.exit(1)
    
    total_deleted_files = 0
    
    # 删除每个用户的文件
    for user_id in DELETE_USER_IDS:
        print(f"\n🗑️  清理用户 {user_id} 的文件...")
        deleted = delete_user_files(user_id)
        total_deleted_files += deleted
    
    # 统计结果
    print("\n" + "=" * 60)
    print("📊 清理完成")
    print(f"  🗑️  删除文件总数: {total_deleted_files}")
    print(f"  ✅ 保留用户: {KEEP_USER_ID}")
    print("=" * 60)
    
    # 显示当前衣橱状态
    print("\n📂 当前衣橱文件状态:")
    wardrobe_dir = Path("/Users/mingyang/Desktop/shunyishang/data/uploads/wardrobe")
    if wardrobe_dir.exists():
        for user_dir in sorted(wardrobe_dir.iterdir()):
            if user_dir.is_dir():
                file_count = len(list(user_dir.glob("*")))
                status = "✅ 保留" if user_dir.name == str(KEEP_USER_ID) else "🗑️  已清理"
                print(f"  用户 {user_dir.name}: {file_count} 个文件 {status}")

if __name__ == "__main__":
    main()
