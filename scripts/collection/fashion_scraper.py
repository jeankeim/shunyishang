"""
国风/简约服饰商品采集框架（列表页 → 详情URL + 基础信息 → CSV/JSON）

采集通道：
1. shopify 通道：请求 {domain}/products.json 公开接口，直接拿到结构化
   商品数据（名称/价格/图片/详情页 handle），最稳定且无风控压力。
2. dom 通道：Playwright 无头浏览器渲染列表页，按站点配置的 CSS 选择器
   提取商品卡片信息，自动翻页。

输出字段（与后续入库/embedding 对齐）：
    site, brand, name, price, price_currency, detail_url, image_url,
    tags, crawled_at

用法：
    python -m scripts.collection.fashion_scraper --site shangxia --format json
    python -m scripts.collection.fashion_scraper --site icicle --format csv --pages 2
    python -m scripts.collection.fashion_scraper --list   # 查看可用站点

依赖：
    pip install requests beautifulsoup4 playwright lxml
    playwright install chromium
"""

import argparse
import asyncio
import csv
import json
import logging
import random
import re
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

from scripts.collection.fashion_sites import (
    ALL_SITES,
    MAX_RETRIES,
    PAGE_LOAD_TIMEOUT,
    REQUEST_INTERVAL,
    DomSite,
    ShopifySite,
    get_site,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("fashion_scraper")

OUTPUT_DIR = Path("data/scraped")

# 常见浏览器 UA（轮换降低指纹识别概率）
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]


def _polite_sleep():
    """请求间隔：随机延迟模拟人类浏览节奏"""
    lo, hi = REQUEST_INTERVAL
    time.sleep(random.uniform(lo, hi))


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _normalize_price(raw: Optional[str]) -> Optional[float]:
    """'¥1,299.00' / '1299元' → 1299.0；解析失败返回 None"""
    if not raw:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)", raw.replace(",", ""))
    return float(m.group(1)) if m else None


# ============================================================
# 通道一：Shopify products.json（结构化、无反爬）
# ============================================================

def crawl_shopify(site: ShopifySite, page_limit: Optional[int] = None) -> List[Dict]:
    """
    遍历 Shopify 公开商品接口，提取基础信息。

    products.json 返回结构：
        {"products": [{"title", "handle", "variants": [{"price"}],
                       "images": [{"src"}], "tags": [...]}]}
    """
    items: List[Dict] = []
    limit_pages = page_limit or site.page_limit

    for page in range(1, limit_pages + 1):
        url = f"{site.products_api}?limit=250&page={page}"
        logger.info(f"[{site.name}] Shopify 接口第 {page} 页: {url}")

        resp = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(
                    url,
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                    timeout=20,
                )
                break
            except requests.RequestException as e:
                logger.warning(f"[{site.name}] 请求失败({attempt}/{MAX_RETRIES}): {e}")
                time.sleep(2 ** attempt)

        if resp is None or resp.status_code != 200:
            code = resp.status_code if resp is not None else "N/A"
            logger.warning(f"[{site.name}] 第 {page} 页状态码 {code}，停止翻页")
            break

        products = resp.json().get("products", [])
        if not products:
            logger.info(f"[{site.name}] 第 {page} 页为空，采集结束")
            break

        for p in products:
            handle = p.get("handle", "")
            variants = p.get("variants") or []
            price = variants[0].get("price") if variants else None
            images = p.get("images") or []
            # 任一 variant 有库存即视为在售（抽样时过滤下架商品）
            available = any(v.get("available") for v in variants)
            # 颜色名来自 variant option（用于抽样分层与转写参考）
            colors = []
            for v in variants:
                opt = (v.get("option1") or "").strip()
                if opt and opt.lower() != "default title" and opt not in colors:
                    colors.append(opt)
            items.append({
                "site": site.name,
                "brand": site.brand_cn,
                "name": p.get("title", "").strip(),
                "price": _normalize_price(str(price)) if price else None,
                "price_currency": "CNY",  # 站点币种需按实际确认，此处默认
                "detail_url": f"https://{site.domain}/products/{handle}",
                "image_url": images[0].get("src") if images else None,
                "tags": ",".join(p.get("tags", [])[:8]),
                "crawled_at": _now_iso(),
                # 抽样/转写流水线专用字段（Shopify 通道独有）
                "product_type": p.get("product_type") or "",
                "vendor": p.get("vendor") or "",
                "all_tags": p.get("tags", []),
                "colors": colors,
                "available": available,
                "body_html": (p.get("body_html") or "")[:1500],
            })

        logger.info(f"[{site.name}] 第 {page} 页采集 {len(products)} 件")
        _polite_sleep()

    return items


# ============================================================
# 通道二：Playwright DOM 解析（自建商城）
# ============================================================

async def crawl_dom(site: DomSite, page_limit: Optional[int] = None) -> List[Dict]:
    """
    Playwright 渲染列表页并翻页，按选择器提取商品卡片。

    反爬对策已内置：真实浏览器指纹 + 随机延迟 + 失败指数退避重试。
    """
    from playwright.async_api import async_playwright

    items: List[Dict] = []
    limit_pages = page_limit or site.page_limit

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
        )
        page = await context.new_page()

        try:
            for page_no in range(1, limit_pages + 1):
                url = site.list_url_tpl.format(page=page_no)
                logger.info(f"[{site.name}] 渲染列表页第 {page_no} 页: {url}")

                ok = False
                for attempt in range(1, MAX_RETRIES + 1):
                    try:
                        await page.goto(url, timeout=PAGE_LOAD_TIMEOUT,
                                        wait_until="domcontentloaded")
                        ok = True
                        break
                    except Exception as e:
                        logger.warning(f"[{site.name}] 加载失败({attempt}/{MAX_RETRIES}): {e}")
                        await asyncio.sleep(2 ** attempt)
                if not ok:
                    logger.warning(f"[{site.name}] 第 {page_no} 页放弃")
                    break

                # 滚动到底部触发懒加载图片与无限滚动内容
                for _ in range(3):
                    await page.mouse.wheel(0, 1200)
                    await asyncio.sleep(random.uniform(0.5, 1.2))

                cards = await page.query_selector_all(site.item_selector)
                if not cards:
                    logger.info(f"[{site.name}] 第 {page_no} 页未命中商品卡片，停止翻页")
                    break

                for card in cards:
                    item = await _extract_card(page, site, card)
                    if item:
                        items.append(item)

                logger.info(f"[{site.name}] 第 {page_no} 页采集 {len(cards)} 张卡片")
                await asyncio.sleep(random.uniform(*REQUEST_INTERVAL))
        finally:
            await browser.close()

    # 按详情 URL 去重（卡片选择器可能嵌套命中）
    seen, unique = set(), []
    for it in items:
        if it["detail_url"] and it["detail_url"] not in seen:
            seen.add(it["detail_url"])
            unique.append(it)
    return unique


async def _extract_card(page, site: DomSite, card) -> Optional[Dict]:
    """从单个商品卡片元素提取 详情URL + 名称/价格/图片"""
    base_url = f"https://{site.domain}"

    # 详情 URL（必需字段，缺失则跳过该卡片）
    link = await card.query_selector(site.link_selector)
    if not link:
        return None
    href = await link.get_attribute("href")
    if not href:
        return None
    detail_url = urljoin(base_url, href)
    if urlparse(detail_url).netloc not in (site.domain, ""):
        return None  # 过滤外链

    # 名称：优先选择器 → 兜底链接文本 / 图片 alt
    name = None
    if site.name_selector:
        el = await card.query_selector(site.name_selector)
        if el:
            name = (await el.inner_text()).strip()
    if not name:
        name = (await link.inner_text()).strip() or await link.get_attribute("title")

    # 价格
    price = None
    if site.price_selector:
        el = await card.query_selector(site.price_selector)
        if el:
            price = _normalize_price(await el.inner_text())

    # 图片：src / data-src（懒加载）
    image_url = None
    if site.image_selector:
        img = await card.query_selector(site.image_selector)
        if img:
            image_url = await img.get_attribute("src") \
                or await img.get_attribute("data-src") \
                or await img.get_attribute("data-original")
            if image_url and image_url.startswith("//"):
                image_url = "https:" + image_url

    return {
        "site": site.name,
        "brand": site.brand_cn,
        "name": name or "",
        "price": price,
        "price_currency": "CNY",
        "detail_url": detail_url,
        "image_url": image_url,
        "tags": ",".join(site.style_tags),
        "crawled_at": _now_iso(),
    }


# ============================================================
# 输出：CSV / JSON
# ============================================================

CSV_FIELDS = [
    "site", "brand", "name", "price", "price_currency",
    "detail_url", "image_url", "tags", "crawled_at",
]


def save_results(items: List[Dict], site_name: str, fmt: str) -> Path:
    """按站点落盘，文件名带日期便于增量对比"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_tag = datetime.now().strftime("%Y%m%d")

    if fmt == "csv":
        path = OUTPUT_DIR / f"{site_name}_{date_tag}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(items)
    else:
        path = OUTPUT_DIR / f"{site_name}_{date_tag}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    logger.info(f"已保存 {len(items)} 条 → {path}")
    return path


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="国风/简约服饰站点采集")
    parser.add_argument("--site", help=f"站点名，可选: {[s.name for s in ALL_SITES]}")
    parser.add_argument("--pages", type=int, default=None, help="覆盖默认翻页上限")
    parser.add_argument("--format", choices=["csv", "json"], default="json")
    parser.add_argument("--list", action="store_true", help="列出全部站点配置")
    args = parser.parse_args()

    if args.list:
        for s in ALL_SITES:
            flag = "✓" if s.enabled else "✗"
            print(f"[{flag}] {s.name:<18} {s.platform:<9} {s.brand_cn}")
        return

    if not args.site:
        parser.error("请指定 --site 或使用 --list 查看可用站点")

    site = get_site(args.site)
    if not site.enabled:
        logger.warning(f"站点 {site.name} 未启用自动采集（{getattr(site, 'note', '强反爬平台')}）")
        sys.exit(2)

    if isinstance(site, ShopifySite):
        items = crawl_shopify(site, page_limit=args.pages)
    elif isinstance(site, DomSite):
        items = asyncio.run(crawl_dom(site, page_limit=args.pages))
    else:
        logger.error(f"站点 {site.name} 无可用采集通道")
        sys.exit(2)

    if items:
        save_results(items, site.name, args.format)
    else:
        logger.warning("未采集到任何商品，请检查站点配置/选择器或网络")


if __name__ == "__main__":
    main()
