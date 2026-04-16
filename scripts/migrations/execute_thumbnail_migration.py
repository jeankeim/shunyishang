#!/usr/bin/env python3
"""
执行缩略图字段迁移脚本
连接到线上数据库并执行 add_thumbnail_url.sql
"""

import psycopg2
from pathlib import Path

# 数据库连接字符串
DB_URL = "postgresql://root:DXQg3VOsxycmWi1h749Z5P6Fa0Kf2j8q@43.129.75.126:30216/zeabur"

def execute_migration():
    """执行数据库迁移"""
    print("=" * 60)
    print("🚀 开始执行缩略图字段迁移")
    print("=" * 60)
    
    try:
        # 连接数据库
        print("\n📡 正在连接数据库...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False  # 使用事务
        cur = conn.cursor()
        print("✅ 数据库连接成功")
        
        # 读取 SQL 文件
        sql_file = Path(__file__).parent / "add_thumbnail_url.sql"
        print(f"\n📄 读取迁移脚本: {sql_file}")
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割 SQL 语句（按分号分割，但跳过注释和空行）
        statements = []
        current_statement = []
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('--'):
                continue
            
            current_statement.append(line)
            
            # 如果行以分号结尾，则是一条完整的语句
            if line.endswith(';'):
                statements.append(' '.join(current_statement))
                current_statement = []
        
        # 添加最后一条语句（如果没有分号）
        if current_statement:
            statements.append(' '.join(current_statement))
        
        print(f"📋 共找到 {len(statements)} 条 SQL 语句\n")
        
        # 执行每条语句
        for i, stmt in enumerate(statements, 1):
            # 跳过验证脚本（SELECT 语句）
            if stmt.strip().upper().startswith('SELECT') or stmt.strip().upper().startswith('--'):
                continue
            
            print(f"⚙️  执行语句 {i}: {stmt[:80]}...")
            
            try:
                cur.execute(stmt)
                
                # 显示受影响行数（如果有）
                if cur.rowcount > 0:
                    print(f"   ✅ 成功，影响 {cur.rowcount} 行")
                else:
                    print(f"   ✅ 成功")
                    
            except Exception as e:
                print(f"   ⚠️  警告: {e}")
                # 不中断，继续执行
        
        # 提交事务
        print("\n💾 提交事务...")
        conn.commit()
        print("✅ 事务提交成功")
        
        # 验证迁移结果
        print("\n" + "=" * 60)
        print("📊 验证迁移结果")
        print("=" * 60)
        
        # 检查字段是否存在
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'items' AND column_name = 'thumbnail_url'
        """)
        column_info = cur.fetchone()
        
        if column_info:
            print(f"\n✅ thumbnail_url 字段已创建")
            print(f"   数据类型: {column_info[1]}")
            print(f"   最大长度: {column_info[2]}")
        else:
            print(f"\n❌ thumbnail_url 字段未找到")
        
        # 统计数据
        cur.execute("""
            SELECT 
                COUNT(*) as total_items,
                COUNT(image_url) as has_image,
                COUNT(thumbnail_url) as has_thumbnail,
                COUNT(image_url) - COUNT(thumbnail_url) as missing_thumbnail
            FROM items
            WHERE image_url IS NOT NULL
        """)
        stats = cur.fetchone()
        
        print(f"\n📈 数据统计:")
        print(f"   总记录数: {stats[0]}")
        print(f"   有图片的记录: {stats[1]}")
        print(f"   已有缩略图URL: {stats[2]}")
        print(f"   缺少缩略图URL: {stats[3]}")
        
        if stats[1] > 0:
            coverage = (stats[2] / stats[1] * 100)
            print(f"   覆盖率: {coverage:.2f}%")
        
        # 查看示例数据
        print(f"\n📋 示例数据 (前5条):")
        cur.execute("""
            SELECT 
                item_code,
                name,
                LEFT(image_url, 60) as image_preview,
                LEFT(COALESCE(thumbnail_url, 'NULL'), 60) as thumb_preview
            FROM items
            WHERE image_url IS NOT NULL
            LIMIT 5
        """)
        
        for row in cur.fetchall():
            print(f"\n   商品编码: {row[0]}")
            print(f"   商品名称: {row[1]}")
            print(f"   原图URL: {row[2]}...")
            print(f"   缩略图URL: {row[3]}...")
        
        print("\n" + "=" * 60)
        print("🎉 迁移完成！")
        print("=" * 60)
        
    except psycopg2.Error as e:
        print(f"\n❌ 数据库错误: {e}")
        if 'conn' in locals():
            conn.rollback()
            print("🔄 事务已回滚")
    except Exception as e:
        print(f"\n❌ 执行错误: {e}")
        if 'conn' in locals():
            conn.rollback()
            print("🔄 事务已回滚")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
            print("\n👋 数据库连接已关闭")

if __name__ == "__main__":
    execute_migration()
