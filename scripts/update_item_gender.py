#!/usr/bin/env python3
"""
更新物品性别字段
将旗袍、半身裙、雪纺衫等女性专属物品从"中性"改为"女"
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.api.core.database import DatabasePool

# 需要更新性别的物品列表
ITEMS_TO_UPDATE = [
    ("ITEM_023", "女"),  # 青绿色旗袍
    ("ITEM_007", "女"),  # 金色金属质感半身裙
    ("ITEM_045", "女"),  # 杏色雪纺衫
]

def update_gender():
    """更新物品性别"""
    try:
        with DatabasePool.get_connection() as conn:
            with conn.cursor() as cur:
                for item_code, gender in ITEMS_TO_UPDATE:
                    cur.execute(
                        "UPDATE items SET gender = %s WHERE item_code = %s",
                        (gender, item_code)
                    )
                    if cur.rowcount > 0:
                        print(f"✅ 更新成功: {item_code} -> {gender}")
                    else:
                        print(f"⚠️ 未找到: {item_code}")
                
                conn.commit()
                print("\n🎉 性别更新完成！")
                
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_gender()
