"""
A' 转写流水线：采集数据 → 配额抽样 → LLM 五行转写 → 向量化 → items 表入库

设计原则：
1. 抽样：补冬夏季节缺口 + 每品类配额 + 颜色分层（避免同色堆叠）
2. 转写：去品牌化中文名 + 五行/面料/温度/季节推断（qwen-plus，JSON 强约束）
3. 合规：不热链品牌图片（image_url 置 NULL），不保留品牌名，
   溯源信息仅存于 attributes_detail.元数据（不对外展示）
4. 断点续跑：转写结果缓存到 data/scraped/transform_cache.json

用法：
    python -m scripts.collection.transform_pipeline --sample-only      # 仅抽样预览
    python -m scripts.collection.transform_pipeline --limit 30 --dry-run  # 小批转写不入库
    python -m scripts.collection.transform_pipeline --import           # 全量转写并入库
"""

import argparse
import json
import logging
import os
import random
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("transform_pipeline")

SCRAPED_DIR = Path("data/scraped")
CACHE_PATH = SCRAPED_DIR / "transform_cache.json"
SAMPLED_PATH = SCRAPED_DIR / "sampled.json"
DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "wuxing_db",
    "user": "wuxing_user", "password": "wuxing_password",
}

VALID_CATEGORIES = {"上装", "下装", "裙装", "外套", "鞋履", "配饰", "饰品", "文玩"}
VALID_ELEMENTS = {"金", "木", "水", "火", "土"}
VALID_STYLES = {"简约", "国潮", "运动", "商务", "甜美", "街头", "文艺", "优雅", "休闲", "性感", "知性", "森系"}
VALID_THICKNESS = {"轻薄", "适中", "加厚", "厚重"}


def _load_env():
    """从 .env 读取 DASHSCOPE_API_KEY（脚本环境无 pydantic-settings）"""
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("DASHSCOPE_API_KEY="):
                os.environ.setdefault("DASHSCOPE_API_KEY", line.split("=", 1)[1].strip())


# ============================================================
# Stage 1: 加载 + 品类映射 + 配额抽样
# ============================================================

# Shopify product_type → items 品类
TYPE_CATEGORY_MAP: Dict[str, str] = {
    # 上装
    "T-shirt": "上装", "Top": "上装", "Shirt": "上装", "Blouse": "上装",
    "Knitwear": "上装", "Sweater": "上装", "Polo": "上装", "Bodysuit": "上装",
    "Jersey": "上装", "Vest": "上装",
    # 下装
    "Trousers": "下装", "Pants": "下装", "Shorts": "下装", "Jeans": "下装", "Denim": "下装",
    # 裙装
    "Dress": "裙装", "Dresses": "裙装", "Skirt": "裙装", "Skirts": "裙装",
    # 外套
    "Coat": "外套", "Jacket": "外套", "Outerwear": "外套", "Blazer": "外套",
    "Trench": "外套", "Cape": "外套", "Parka": "外套",
    # 鞋履
    "Shoes": "鞋履", "Boots": "鞋履", "Sneakers": "鞋履", "Sandals": "鞋履",
    "Slippers": "鞋履", "Loafers": "鞋履",
    # 配饰
    "Bag": "配饰", "Bags": "配饰", "Scarf": "配饰", "Hat": "配饰", "Belt": "配饰",
    "Gloves": "配饰", "Socks": "配饰", "Sunglasses": "配饰",
    "Small / Medium Leathergoods": "配饰",
    # 饰品
    "Jewellery": "饰品", "Jewelry": "饰品", "Fashion Jewellery": "饰品",
    "Earrings": "饰品", "Necklace": "饰品", "Ring": "饰品", "Bracelet": "饰品",
}
# 明确排除的品类（泳装/家居/香氛等与穿搭库无关）
SKIP_TYPES = {"Swimwear", "Home", "Fragrance", "Lifestyle", "Objects", "Tea", "Tableware"}

# 每品类配额与季节优先级（winter/summer/none）
CATEGORY_QUOTA = {
    "外套": {"quota": 60, "season": "winter"},   # 库内冬季最薄（18件）
    "上装": {"quota": 55, "season": "summer"},   # 夏季上装缺口大，冬季针织由外套配额兼顾
    "下装": {"quota": 45, "season": "summer"},
    "裙装": {"quota": 45, "season": "summer"},
    "配饰": {"quota": 35, "season": "none"},
    "鞋履": {"quota": 30, "season": "none"},
    "饰品": {"quota": 30, "season": "none"},
}

WINTER_TYPES = {"Knitwear", "Sweater", "Coat", "Jacket", "Outerwear", "Blazer", "Trench", "Parka", "Boots", "Gloves", "Scarf"}
SUMMER_TYPES = {"Dress", "Dresses", "Skirt", "Skirts", "Shorts", "Top", "T-shirt", "Sandals", "Shirt", "Blouse"}

# 颜色族归一（用于分层抽样，避免同色堆叠）
COLOR_FAMILIES = {
    "黑": ["black", "noir"], "白": ["white", "ecru", "ivory", "cream", "blanc"],
    "灰": ["grey", "gray", "gris"], "棕": ["brown", "chocolate", "marron", "camel", "tan", "khaki", "beige", "sand", "taupe"],
    "蓝": ["blue", "navy", "denim", "indigo", "bleu"], "绿": ["green", "olive", "vert", "sage"],
    "红": ["red", "burgundy", "rouge", "bordeaux", "maroon"], "粉": ["pink", "rose", "blush"],
    "黄": ["yellow", "mustard", "gold", "jaune", "ocre"], "紫": ["purple", "violet", "lilac"],
}


def _color_family(colors: List[str]) -> str:
    """从 variant 颜色名归一到颜色族"""
    text = " ".join(colors).lower()
    for fam, kws in COLOR_FAMILIES.items():
        if any(kw in text for kw in kws):
            return fam
    return "其他"


def _season_signal(item: Dict) -> Dict[str, bool]:
    """判断商品的冬/夏信号（tag 季前缀 + 品类先验 + 描述关键词）"""
    tags_text = " ".join(item.get("all_tags", [])).lower()
    body = (item.get("body_html") or "").lower()
    ptype = item.get("product_type", "")
    return {
        "winter": "fw" in tags_text or "winter" in tags_text or ptype in WINTER_TYPES
                  or any(w in body for w in ["cashmere", "wool", "羊绒", "羊毛"]),
        "summer": "ss" in tags_text or "summer" in tags_text or ptype in SUMMER_TYPES
                  or any(w in body for w in ["linen", "silk", "亚麻", "真丝"]),
    }


def load_scraped() -> List[Dict]:
    """加载最新一批采集数据"""
    items = []
    for f in sorted(SCRAPED_DIR.glob("*_2*.json")):
        if f.name in ("transform_cache.json", "sampled.json"):
            continue
        try:
            items.extend(json.loads(f.read_text(encoding="utf-8")))
        except Exception as e:
            logger.warning(f"跳过 {f.name}: {e}")
    logger.info(f"加载原始采集数据 {len(items)} 条")
    return items


def sample_items(raw: List[Dict]) -> List[Dict]:
    """补冬夏缺口 + 品类配额 + 颜色分层抽样"""
    # 1. 过滤与品类映射
    pools: Dict[str, List[Dict]] = defaultdict(list)
    for it in raw:
        if not it.get("available", True):
            continue
        ptype = it.get("product_type", "")
        if ptype in SKIP_TYPES:
            continue
        cat = TYPE_CATEGORY_MAP.get(ptype)
        if not cat or cat not in CATEGORY_QUOTA:
            continue
        sig = _season_signal(it)
        it["_category"] = cat
        it["_winter"] = sig["winter"]
        it["_summer"] = sig["summer"]
        it["_color_family"] = _color_family(it.get("colors", []))
        pools[cat].append(it)

    # 2. 每品类：按季节优先排序 + 颜色族轮转取样
    sampled = []
    for cat, cfg in CATEGORY_QUOTA.items():
        pool = pools.get(cat, [])
        if cfg["season"] == "winter":
            pool.sort(key=lambda x: (not x["_winter"], random.random()))
        elif cfg["season"] == "summer":
            pool.sort(key=lambda x: (not x["_summer"], random.random()))
        else:
            random.shuffle(pool)

        # 颜色族分桶轮转，保证同品类内颜色多样
        buckets: Dict[str, List[Dict]] = defaultdict(list)
        for it in pool:
            buckets[it["_color_family"]].append(it)
        picked, order = [], list(buckets.keys())
        random.shuffle(order)
        while len(picked) < cfg["quota"] and any(buckets.values()):
            for fam in order:
                if buckets[fam]:
                    picked.append(buckets[fam].pop(0))
                if len(picked) >= cfg["quota"]:
                    break
        sampled.extend(picked)
        logger.info(f"[抽样] {cat}: 候选 {len(pool)} → 取 {len(picked)}（配额 {cfg['quota']}，优先{cfg['season'] or '均衡'}）")

    return sampled


# ============================================================
# Stage 2: LLM 转写（去品牌化 + 五行打标）
# ============================================================

TRANSFORM_PROMPT = """你是五行服饰数据标注专家。将一件采集到的商品转写为中文抽象单品（用于穿搭推荐库）。

商品信息：
- 原标题：{title}
- 品类线索：{product_type}
- 可选颜色：{colors}
- 描述摘录：{body}

请输出严格 JSON（不输出其他内容），字段如下：
{{
  "name_cn": "中文单品名，格式：颜色+面料+款式（如'黑色重磅棉圆领T恤'），禁止出现任何品牌名/外文/型号",
  "category": "必须是：上装/下装/裙装/外套/鞋履/配饰/饰品 之一",
  "primary_element": "主五行，金木水火土之一（按颜色为主：白金银→金，黑深蓝→水，绿青→木，红紫橙→火，黄棕驼→土）",
  "secondary_element": "次五行或 null",
  "energy_intensity": 0.0到1.0的数字（色彩鲜艳饱和则高，素雅则低）,
  "color": "中文颜色名（如'炭黑'、'燕麦色'）",
  "color_hex": "近似色值如#1A1A1A",
  "material": "面料中文名；描述中未提及时按品类常识推断最可能面料",
  "material_inferred": true或false（描述未明确提及面料时为true）,
  "style": "必须是：简约/优雅/商务/休闲/文艺/知性/运动/街头/森系 之一",
  "gender": "男/女/中性",
  "applicable_seasons": ["春","夏","秋","冬"]的子集，按面料厚度与款式判断",
  "applicable_weather": ["晴","多云","阴","雨","风","炎热","寒冷"]的子集",
  "temperature_range": {{"最低": 数字, "最高": 数字}}（适穿摄氏度区间，按面料厚度判断）,
  "functionality": {{"保暖": bool, "透气": bool, "防晒": bool, "防水": bool, "抗皱": bool}},
  "thickness_level": "轻薄/适中/加厚/厚重 之一",
  "tags": [2到4个场景标签，如通勤/约会/旅行/休闲/正式]
}}

约束：只依据给定信息推断，不得编造品牌、价格、工艺细节；name_cn 必须完全去品牌化。"""


def _get_llm_client():
    from openai import OpenAI
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 DASHSCOPE_API_KEY")
    return OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")


def transform_one(client, item: Dict) -> Optional[Dict]:
    """单件转写：LLM 输出 JSON → 字段校验（失败重试 1 次）"""
    body = re.sub(r"<[^>]+>", " ", item.get("body_html") or "")[:400]
    prompt = TRANSFORM_PROMPT.format(
        title=item.get("name", ""),
        product_type=item.get("product_type", "未知"),
        colors=", ".join(item.get("colors", [])[:6]) or "未知",
        body=body or "无",
    )

    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "你是服饰五行标注专家，严格按 JSON 输出。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
                timeout=60,
            )
            data = json.loads(resp.choices[0].message.content)
        except Exception as e:
            logger.warning(f"转写调用失败({attempt + 1}/2) {item.get('name')}: {e}")
            time.sleep(1.5)
            continue

        # 字段校验
        if (data.get("category") in VALID_CATEGORIES
                and data.get("primary_element") in VALID_ELEMENTS
                and data.get("name_cn")
                and data.get("thickness_level") in VALID_THICKNESS
                and isinstance(data.get("temperature_range"), dict)):
            return data
        logger.warning(f"转写校验失败({attempt + 1}/2) {item.get('name')}: {data.get('category')}/{data.get('primary_element')}")

    return None


def transform_batch(sampled: List[Dict], limit: Optional[int] = None, workers: int = 4) -> List[Dict]:
    """批量转写（带缓存断点续跑 + 多线程并发，OpenAI client 线程安全）"""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    cache: Dict[str, Dict] = {}
    if CACHE_PATH.exists():
        cache = {r["_source_url"]: r for r in json.loads(CACHE_PATH.read_text(encoding="utf-8"))}
        logger.info(f"已加载转写缓存 {len(cache)} 条")

    client = _get_llm_client()
    todo = sampled[:limit] if limit else sampled
    lock = threading.Lock()
    done_count = [0]

    def _flush_cache():
        CACHE_PATH.write_text(
            json.dumps(list(cache.values()), ensure_ascii=False, indent=1), encoding="utf-8")

    def _process(item: Dict) -> Optional[Dict]:
        url = item.get("detail_url", "")
        with lock:
            if url in cache:
                return cache[url]

        data = transform_one(client, item)
        if data:
            data["_source_url"] = url
            data["_source_site"] = item.get("site")
            data["_winter"] = item.get("_winter")
            data["_summer"] = item.get("_summer")
            with lock:
                cache[url] = data
                done_count[0] += 1
                n = done_count[0]
                if n % 20 == 0:
                    _flush_cache()
            logger.info(f"✓ {item.get('name')} → {data['name_cn']}（{data['category']}/{data['primary_element']}）")
        else:
            logger.warning(f"✗ {item.get('name')} 转写失败，跳过")
        time.sleep(0.2)  # 并发下的轻量限速
        return data

    logger.info(f"开始转写: {len(todo)} 件，并发 {workers} 路")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = [r for r in ex.map(_process, todo) if r]

    _flush_cache()
    logger.info(f"转写完成: {len(results)} 条（缓存累计 {len(cache)} 条）")
    return results


# ============================================================
# Stage 3: Embedding（与 import_seed.build_context_text 同构）
# ============================================================

def build_context_text(r: Dict) -> str:
    """构造向量化文本（对齐 items 表语义结构）"""
    text = f"这是一件{r['name_cn']}，属于{r['category']}类别。"
    text += f"颜色是{r.get('color', '')}，五行属{r.get('primary_element', '')}，能量强度{r.get('energy_intensity', 0.5)}。"
    text += f"面料为{r.get('material', '')}。款式风格为{r.get('style', '')}。"
    tags = ", ".join(r.get("tags", []))
    if tags:
        text += f"适合场景：{tags}。"
    return text


def gen_embeddings(texts: List[str]) -> List[List[float]]:
    """DashScope text-embedding-v3（逐条调用，带重试，与 embedding_service 行为一致）"""
    import dashscope
    from dashscope import TextEmbedding
    dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY")
    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

    vecs = []
    for t in texts:
        for attempt in range(3):
            try:
                resp = TextEmbedding.call(model="text-embedding-v3", input=t)
                if resp.status_code == 200:
                    vecs.append(resp.output["embeddings"][0]["embedding"])
                    break
                logger.warning(f"embedding 业务错误: {resp.code} {resp.message}")
            except Exception as e:
                logger.warning(f"embedding 网络异常({attempt + 1}/3): {e}")
                time.sleep(1.5 * (attempt + 1))
        else:
            vecs.append(None)  # 允许 NULL 向量先入库，后续补生成
    return vecs


# ============================================================
# Stage 4: 入库（字段结构与 import_seed.py 完全对齐）
# ============================================================

def import_to_db(results: List[Dict], dry_run: bool = False):
    """写入 items 表：item_code 续接现有最大编号"""
    import psycopg2
    from psycopg2.extras import execute_values

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(CAST(SUBSTRING(item_code FROM 6) AS INTEGER)), 0) FROM items WHERE item_code LIKE 'ITEM_%'")
    start_no = cur.fetchone()[0]
    logger.info(f"item_code 从 ITEM_{start_no + 1:03d} 开始续编")

    texts = [build_context_text(r) for r in results]
    logger.info("生成 embedding 中...")
    embeddings = gen_embeddings(texts)

    values = []
    for i, r in enumerate(results):
        attributes_detail = {
            "颜色": {"名称": r.get("color"), "色值": r.get("color_hex"),
                     "主五行": r.get("primary_element"), "能量强度": r.get("energy_intensity")},
            "面料": {"名称": r.get("material"), "推断": r.get("material_inferred", False)},
            "款式": {"风格": r.get("style"), "细节": []},
            "元数据": {"来源": "A'转写", "source_site": r.get("_source_site"), "置信度": 0.85},
        }
        values.append((
            f"ITEM_{start_no + 1 + i:03d}",
            r["name_cn"],
            r["category"],
            r.get("primary_element"),
            r.get("secondary_element"),
            r.get("energy_intensity", 0.5),
            r.get("gender", "中性"),
            json.dumps(attributes_detail, ensure_ascii=False),
            embeddings[i],
            json.dumps(r.get("applicable_weather", []), ensure_ascii=False),
            json.dumps(r.get("applicable_seasons", []), ensure_ascii=False),
            json.dumps(r.get("temperature_range", {}), ensure_ascii=False),
            json.dumps(r.get("functionality", {}), ensure_ascii=False),
            r.get("thickness_level", "适中"),
        ))

    if dry_run:
        logger.info(f"[dry-run] 跳过写入，共 {len(values)} 条待入库")
        sample = values[0]
        logger.info(f"[dry-run] 示例: {sample[0]} | {sample[1]} | {sample[2]} | {sample[3]} | 向量维度 {len(sample[8]) if sample[8] else 'NULL'}")
        conn.close()
        return

    sql = """
    INSERT INTO items (item_code, name, category, primary_element, secondary_element,
                       energy_intensity, gender, attributes_detail, embedding,
                       applicable_weather, applicable_seasons, temperature_range,
                       functionality, thickness_level)
    VALUES %s
    ON CONFLICT (item_code) DO NOTHING
    """
    execute_values(cur, sql, values)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM items")
    logger.info(f"入库完成: 新增 {len(values)} 条，items 总数 {cur.fetchone()[0]}")
    conn.close()


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="A' 转写流水线")
    parser.add_argument("--sample-only", action="store_true", help="仅抽样并保存预览，不调用 LLM")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 件（小批验证）")
    parser.add_argument("--dry-run", action="store_true", help="转写+向量化但不写库")
    parser.add_argument("--import", dest="do_import", action="store_true", help="实际写入 items 表")
    parser.add_argument("--workers", type=int, default=4, help="转写并发路数")
    args = parser.parse_args()

    _load_env()
    random.seed(42)  # 抽样可复现

    raw = load_scraped()
    sampled = sample_items(raw)
    SAMPLED_PATH.write_text(json.dumps(sampled, ensure_ascii=False, indent=1), encoding="utf-8")
    logger.info(f"抽样总数: {len(sampled)} → {SAMPLED_PATH}")

    # 抽样分布报告
    matrix = defaultdict(lambda: {"冬": 0, "夏": 0, "其他": 0})
    for it in sampled:
        season = "冬" if it["_winter"] else ("夏" if it["_summer"] else "其他")
        matrix[it["_category"]][season] += 1
    logger.info("抽样季节分布: " + " | ".join(
        f"{cat}({v['冬']}冬/{v['夏']}夏/{v['其他']}他)" for cat, v in matrix.items()))

    if args.sample_only:
        return

    results = transform_batch(sampled, limit=args.limit, workers=args.workers)
    if not results:
        logger.error("无可入库数据")
        return

    if args.do_import and not args.dry_run:
        import_to_db(results, dry_run=False)
    else:
        import_to_db(results, dry_run=True)


if __name__ == "__main__":
    main()
