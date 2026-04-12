#!/usr/bin/env python3
"""
导入 user_wardrobe SQL 文件到 Zeabur 数据库
"""

import subprocess
import sys
import os

# Zeabur 数据库连接信息
# TODO: 从 Zeabur 控制台获取这些值
DB_CONFIG = {
    "host": os.getenv("ZEABUR_DB_HOST", "PLEASE_FILL_FROM_ZEABUR_CONSOLE"),
    "port": os.getenv("ZEABUR_DB_PORT", "5432"),
    "database": os.getenv("ZEABUR_DB_NAME", "zeabur"),
    "user": os.getenv("ZEABUR_DB_USER", "root"),
    "password": os.getenv("ZEABUR_DB_PASSWORD", "DXQg3VOsxycmWi1h749Z5P6Fa0Kf2j8q")
}

SQL_FILE = "/Users/mingyang/Desktop/shunyishang/scripts/export_wardrobe_to_zeabur.sql"


def check_psql_available():
    """检查 psql 是否可用"""
    try:
        result = subprocess.run(
            ["psql", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ 找到 psql: {result.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("❌ 未找到 psql 客户端")
    print("\n解决方案：")
    print("1. 安装 PostgreSQL 客户端: brew install libpq")
    print("2. 或者使用 Zeabur Console 的 SQL 编辑器直接导入")
    print("3. 或者使用 pgAdmin/DBeaver 等 GUI 工具")
    return False


def import_sql_with_psql():
    """使用 psql 导入 SQL 文件"""
    if not check_psql_available():
        return False
    
    # 检查 SQL 文件是否存在
    if not os.path.exists(SQL_FILE):
        print(f"❌ SQL 文件不存在: {SQL_FILE}")
        return False
    
    # 检查配置是否完整
    if "PLEASE_FILL" in DB_CONFIG["host"]:
        print("❌ 数据库 host 未配置！")
        print("\n请从 Zeabur 控制台获取数据库连接信息：")
        print("1. 打开 Zeabur Console")
        print("2. 找到 PostgreSQL 服务")
        print("3. 复制 Connection String 或 Host/Port 信息")
        print("\n然后设置环境变量：")
        print("  export ZEABUR_DB_HOST=<your-host>")
        print("  export ZEABUR_DB_PORT=<your-port>")
        print("  export ZEABUR_DB_NAME=zeabur")
        print("  export ZEABUR_DB_USER=root")
        print("  export ZEABUR_DB_PASSWORD=DXQg3VOsxycmWi1h749Z5P6Fa0Kf2j8q")
        return False
    
    # 构建 psql 命令
    cmd = [
        "psql",
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}",
        "-f", SQL_FILE,
        "-v", "ON_ERROR_STOP=1"  # 遇到错误时停止
    ]
    
    print(f"\n📤 开始导入数据到 Zeabur 数据库...")
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Port: {DB_CONFIG['port']}")
    print(f"   Database: {DB_CONFIG['database']}")
    print(f"   User: {DB_CONFIG['user']}")
    print(f"   SQL 文件: {SQL_FILE}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            timeout=300,  # 5分钟超时
            capture_output=False  # 直接输出到终端
        )
        
        if result.returncode == 0:
            print("\n✅ 导入成功！")
            return True
        else:
            print(f"\n❌ 导入失败，退出码: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ 导入超时（超过5分钟）")
        return False
    except Exception as e:
        print(f"\n❌ 导入异常: {e}")
        return False


def print_manual_import_guide():
    """打印手动导入指南"""
    print("\n" + "="*60)
    print("📋 手动导入方案")
    print("="*60)
    print("\n方案 1: 使用 Zeabur Console（推荐）")
    print("-" * 60)
    print("1. 打开 https://zeabur.com")
    print("2. 进入你的项目")
    print("3. 找到 PostgreSQL 服务")
    print("4. 点击「数据库管理」或「SQL 编辑器」")
    print(f"5. 复制以下文件内容并执行：")
    print(f"   {SQL_FILE}")
    print(f"6. 文件大小: 1.4 MB，可能需要几分钟")
    
    print("\n方案 2: 使用 psql 命令行")
    print("-" * 60)
    print("# 安装 psql 客户端（如果没有）")
    print("brew install libpq")
    print()
    print("# 导入 SQL 文件")
    print("PGPASSWORD=DXQg3VOsxycmWi1h749Z5P6Fa0Kf2j8q psql \\")
    print("  -h <YOUR_HOST> \\")
    print("  -p <YOUR_PORT> \\")
    print("  -U root \\")
    print("  -d zeabur \\")
    print(f"  -f {SQL_FILE}")
    
    print("\n方案 3: 使用 GUI 工具（pgAdmin/DBeaver）")
    print("-" * 60)
    print("1. 下载并安装 pgAdmin 或 DBeaver")
    print("2. 创建新连接：")
    print("   - Host: <从Zeabur获取>")
    print("   - Port: <从Zeabur获取>")
    print("   - Database: zeabur")
    print("   - Username: root")
    print("   - Password: DXQg3VOsxycmWi1h749Z5P6Fa0Kf2j8q")
    print("3. 连接后执行 SQL 文件")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    print("="*60)
    print("🚀 WuXing AI Stylist - 衣橱数据导入工具")
    print("="*60)
    print()
    
    # 尝试自动导入
    success = import_sql_with_psql()
    
    if not success:
        print_manual_import_guide()
    
    print()
