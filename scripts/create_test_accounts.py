"""
创建测试账号脚本
测试期间使用，生成易于记忆的测试账号
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.api.core.database import DatabasePool
from apps.api.core.security import get_password_hash, generate_user_code

# 测试账号列表（手机号、密码、昵称、性别）
TEST_ACCOUNTS = [
    ("13800000001", "test1234", "小明", "男"),
    ("13800000002", "test1234", "小红", "女"),
    ("13800000003", "test1234", "小刚", "男"),
    ("13800000004", "test1234", "小美", "女"),
    ("13800000005", "test1234", "测试员", "男"),
]

def create_test_accounts():
    """创建测试账号"""
    print("=" * 50)
    print("顺衣尚 - 测试账号创建工具")
    print("=" * 50)
    
    created = []
    skipped = []
    
    with DatabasePool.get_connection() as conn:
        with conn.cursor() as cur:
            for phone, password, nickname, gender in TEST_ACCOUNTS:
                # 检查是否已存在
                cur.execute("SELECT id FROM users WHERE phone = %s", (phone,))
                if cur.fetchone():
                    skipped.append(phone)
                    print(f"    {nickname} ({phone}) - 已存在，跳过")
                    continue
                
                # 创建用户
                user_code = generate_user_code()
                password_hash = get_password_hash(password)
                
                cur.execute(
                    """
                    INSERT INTO users (user_code, phone, email, password_hash, nickname, gender)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_code, phone, None, password_hash, nickname, gender)
                )
                user_id = cur.fetchone()[0]
                conn.commit()
                created.append((nickname, phone, password))
                print(f"  ✅ {nickname} ({phone}) - 创建成功 (ID: {user_id})")
    
    print()
    print("=" * 50)
    print("测试账号信息（统一密码: test1234）")
    print("=" * 50)
    for nickname, phone, password in created:
        print(f"  昵称: {nickname}  手机号: {phone}  密码: {password}")
    
    if skipped:
        print(f"\n  跳过 {len(skipped)} 个已存在账号")
    
    print()
    print("登录方式: 在前端登录页输入手机号和密码即可")
    print("=" * 50)


if __name__ == "__main__":
    create_test_accounts()
