"""更新数据库中物品的性别字段"""
import json
import psycopg2

# 读取种子数据
with open('data/seeds/seed_data_100.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 构建物品ID到性别的映射
gender_map = {}
for item in data:
    gender_map[item['物品 ID']] = item.get('适用性别', '中性')

# 连接数据库
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='wuxing_db',
    user='wuxing_user',
    password='wuxing_password'
)
cur = conn.cursor()

# 更新性别字段
for item_code, gender in gender_map.items():
    cur.execute('UPDATE items SET gender = %s WHERE item_code = %s', (gender, item_code))

conn.commit()
print(f'已更新 {len(gender_map)} 条记录的性别字段')

# 验证
cur.execute('SELECT gender, COUNT(*) FROM items GROUP BY gender')
results = cur.fetchall()
print()
print('=== 数据库中性别分布 ===')
for row in results:
    print(f'{row[0]}: {row[1]}件')

cur.close()
conn.close()
