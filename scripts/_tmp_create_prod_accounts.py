"""临时脚本：在线上数据库创建测试账号"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATABASE_URL'] = 'postgresql://root:23iMH7ud61owa0bKpePLq98UCDgX45TY@163.7.19.105:30395/zeabur'

from apps.api.core.database import DatabasePool
from apps.api.core.security import get_password_hash, generate_user_code

TEST_ACCOUNTS = [
    ('13800000001', 'test1234', '小明', '男'),
    ('13800000002', 'test1234', '小红', '女'),
    ('13800000003', 'test1234', '小刚', '男'),
    ('13800000004', 'test1234', '小美', '女'),
    ('13800000005', 'test1234', '测试员', '男'),
]

with DatabasePool.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT count(*) FROM users')
        print('当前用户数:', cur.fetchone()[0])
        
        for phone, password, nickname, gender in TEST_ACCOUNTS:
            cur.execute('SELECT id FROM users WHERE phone = %s', (phone,))
            if cur.fetchone():
                print(f'  跳过 {nickname} ({phone}) - 已存在')
                continue
            user_code = generate_user_code()
            password_hash = get_password_hash(password)
            cur.execute(
                'INSERT INTO users (user_code, phone, email, password_hash, nickname, gender) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id',
                (user_code, phone, None, password_hash, nickname, gender)
            )
            uid = cur.fetchone()[0]
            conn.commit()
            print(f'  OK {nickname} ({phone}) ID={uid}')

print('线上测试账号创建完成')
