#!/usr/bin/env python3
"""
导出 items 表数据为 SQL INSERT 语句，用于导入线上数据库
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json

DB_CONFIG = {
    "host": "localhost",
    "database": "wuxing_db",
    "user": "wuxing_user",
    "password": "wuxing_password"
}

OUTPUT_FILE = "/Users/mingyang/Desktop/shunyishang/scripts/export_items_to_zeabur.sql"


def log(level: str, message: str):
    print(f"[{level}] {message}")


def escape_sql(s):
    """转义 SQL 字符串"""
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''") + "'"


def export_items():
    log("INFO", "=== 开始导出 items 数据 ===")
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    item_code, name, category, primary_element, secondary_element,
                    energy_intensity, gender, attributes_detail, embedding,
                    applicable_weather, applicable_seasons, temperature_range,
                    functionality, thickness_level, image_url
                FROM items
                ORDER BY item_code
            """)
            
            items = cur.fetchall()
            total = len(items)
            
            log("INFO", f"查询到 {total} 条记录")
            
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write("-- =====================================================\n")
                f.write("-- WuXing AI Stylist - Items 数据导入脚本\n")
                f.write(f"-- 记录数: {total}\n")
                f.write("-- 用于导入 Zeabur 数据库\n")
                f.write("-- =====================================================\n\n")
                
                for idx, item in enumerate(items, 1):
                    if idx % 20 == 0:
                        log("INFO", f"处理进度: {idx}/{total}")
                    
                    # 转换中文键为英文键
                    def convert_temperature_range(temp_dict):
                        """转换温度范围: {最低, 最高} -> {min, max}"""
                        if not temp_dict:
                            return {}
                        return {
                            "min": temp_dict.get("最低", temp_dict.get("min")),
                            "max": temp_dict.get("最高", temp_dict.get("max"))
                        }
                    
                    def convert_weather_list(weather_list):
                        """转换天气列表: 中文 -> 英文"""
                        weather_map = {
                            "晴": "sunny", "炎热": "hot", "寒冷": "cold",
                            "多云": "cloudy", "阴": "overcast", "雨": "rainy",
                            "雪": "snowy", "霾": "hazy"
                        }
                        if not weather_list:
                            return []
                        return [weather_map.get(w, w) for w in weather_list]
                    
                    def convert_season_list(season_list):
                        """转换季节列表: 中文 -> 英文"""
                        season_map = {
                            "春": "spring", "夏": "summer",
                            "秋": "autumn", "冬": "winter"
                        }
                        if not season_list:
                            return []
                        return [season_map.get(s, s) for s in season_list]
                    
                    def convert_functionality(func_dict):
                        """转换功能特性: 中文 -> 英文"""
                        func_map = {
                            "保暖": "warm", "透气": "breathable",
                            "速干": "quick_dry", "防晒": "sun_protection",
                            "防水": "waterproof"
                        }
                        if not func_dict:
                            return {}
                        return {func_map.get(k, k): v for k, v in func_dict.items()}
                    
                    # 处理 JSONB 字段（转换中英文）
                    attr = escape_sql(json.dumps(item['attributes_detail'], ensure_ascii=False) if item['attributes_detail'] else '{}')
                    weather = escape_sql(json.dumps(convert_weather_list(item['applicable_weather']), ensure_ascii=False))
                    seasons = escape_sql(json.dumps(convert_season_list(item['applicable_seasons']), ensure_ascii=False))
                    temp = escape_sql(json.dumps(convert_temperature_range(item['temperature_range']), ensure_ascii=False))
                    func = escape_sql(json.dumps(convert_functionality(item['functionality']), ensure_ascii=False))
                    
                    # 处理 embedding 向量（确保是列表格式）
                    if item['embedding']:
                        emb_data = item['embedding']
                        # 如果是字符串，解析成列表
                        if isinstance(emb_data, str):
                            try:
                                emb_list = json.loads(emb_data)
                            except:
                                emb_list = [float(x) for x in emb_data.strip('[]').split(',') if x.strip()]
                        elif isinstance(emb_data, (list, tuple)):
                            emb_list = emb_data
                        else:
                            emb_list = list(emb_data)
                        
                        # 生成紧凑格式的向量字符串
                        emb = "[" + ",".join(str(float(x)) for x in emb_list) + "]"
                        embedding = f"'{emb}'::vector"
                    else:
                        embedding = "NULL"
                    
                    energy = item['energy_intensity'] if item['energy_intensity'] is not None else 'NULL'
                    
                    sql = f"""INSERT INTO items (item_code, name, category, primary_element, secondary_element, energy_intensity, gender, attributes_detail, embedding, applicable_weather, applicable_seasons, temperature_range, functionality, thickness_level, image_url) VALUES ({escape_sql(item['item_code'])}, {escape_sql(item['name'])}, {escape_sql(item['category'])}, {escape_sql(item['primary_element'])}, {escape_sql(item['secondary_element'])}, {energy}, {escape_sql(item['gender'])}, {attr}, {embedding}, {weather}, {seasons}, {temp}, {func}, {escape_sql(item['thickness_level'])}, {escape_sql(item['image_url'])}) ON CONFLICT (item_code) DO UPDATE SET name = EXCLUDED.name, category = EXCLUDED.category, primary_element = EXCLUDED.primary_element, secondary_element = EXCLUDED.secondary_element, energy_intensity = EXCLUDED.energy_intensity, gender = EXCLUDED.gender, attributes_detail = EXCLUDED.attributes_detail, embedding = EXCLUDED.embedding, applicable_weather = EXCLUDED.applicable_weather, applicable_seasons = EXCLUDED.applicable_seasons, temperature_range = EXCLUDED.temperature_range, functionality = EXCLUDED.functionality, thickness_level = EXCLUDED.thickness_level, image_url = EXCLUDED.image_url, updated_at = CURRENT_TIMESTAMP;
"""
                    f.write(sql)
                
                log("INFO", f"\n✅ 导出完成！")
                log("INFO", f"📁 文件位置: {OUTPUT_FILE}")
                log("INFO", f"📊 总记录数: {total}")
                
    finally:
        conn.close()


if __name__ == "__main__":
    export_items()
