"""
国风/简约高品质服饰站点采集配置

每个站点声明：
- platform: 建站平台/采集通道类型
    * shopify  : Shopify 站，走公开 products.json 接口（结构化、最稳、无反爬压力）
    * dom      : 自建商城，走 Playwright 渲染 + CSS 选择器解析
    * platform : 电商平台店铺（天猫/京东），强反爬，默认关闭，仅作占位说明
- enabled: 是否允许采集（platform 类一律 False，需人工/AI 辅助方式另行处理）
- 各类型对应的入口与解析规则

注意：新增站点前先人工确认 robots.txt 与服务条款，个人用途小规模低频采集。
"""

from dataclasses import dataclass, field
from typing import List, Optional

# 全局采集行为参数
DEFAULT_PAGE_LIMIT = 3          # 每站最多翻页数（控制量级，礼貌采集）
REQUEST_INTERVAL = (2.0, 5.0)   # 请求间隔随机区间（秒），模拟人类浏览节奏
PAGE_LOAD_TIMEOUT = 30_000      # Playwright 页面加载超时（毫秒）
MAX_RETRIES = 3                 # 单页失败重试次数（指数退避）


@dataclass
class ShopifySite:
    """Shopify 站：直接用 https://<domain>/products.json?page=N&limit=250"""
    name: str
    domain: str
    brand_cn: str
    style_tags: List[str]
    price_band: str
    enabled: bool = True
    platform: str = "shopify"
    page_limit: int = DEFAULT_PAGE_LIMIT

    @property
    def products_api(self) -> str:
        return f"https://{self.domain}/products.json"


@dataclass
class DomSite:
    """自建商城：Playwright 渲染后按 CSS 选择器解析列表页"""
    name: str
    domain: str
    brand_cn: str
    style_tags: List[str]
    price_band: str
    # 列表页入口：{page} 为页码占位符（首页为第 1 页）
    list_url_tpl: str
    item_selector: str                      # 单个商品卡片
    link_selector: str                      # 卡片内详情页链接
    name_selector: Optional[str] = None     # 名称（None 时用链接文本/alt 兜底）
    price_selector: Optional[str] = None    # 价格
    image_selector: Optional[str] = None    # 图片
    next_page_selector: Optional[str] = None  # "下一页"按钮（可选，兜底翻页）
    enabled: bool = True
    platform: str = "dom"
    page_limit: int = DEFAULT_PAGE_LIMIT


@dataclass
class PlatformShop:
    """电商平台店铺：强反爬（淘宝/京东），默认禁用，仅作清单登记"""
    name: str
    domain: str
    brand_cn: str
    style_tags: List[str]
    price_band: str
    enabled: bool = False
    platform: str = "platform"
    note: str = ""


# ============================================================
# 站点清单
# ============================================================

SHOPIFY_SITES: List[ShopifySite] = [
    ShopifySite(
        name="shangxia", domain="www.shangxia.com", brand_cn="SHANG XIA 上下",
        style_tags=["国风", "东方美学", "高客单"], price_band="¥1000-100000+",
    ),
    ShopifySite(
        name="toteme", domain="toteme.com", brand_cn="TOTEME",
        style_tags=["极简", "静奢"], price_band="¥1500-20000",
    ),
    ShopifySite(
        name="lemaire", domain="www.lemaire.fr", brand_cn="LEMAIRE",
        style_tags=["极简", "法式剪裁"], price_band="¥2000-30000",
    ),
]

DOM_SITES: List[DomSite] = [
    DomSite(
        name="icicle", domain="www.icicle.com.cn", brand_cn="ICICLE 之禾",
        style_tags=["极简", "天然面料", "天人合一"], price_band="¥1000-20000",
        list_url_tpl="https://www.icicle.com.cn/cn/women/?page={page}",
        item_selector="li.product-item, div.product-item, [class*='product']",
        link_selector="a[href*='/cn/']",
        name_selector="h2, h3, [class*='title'], [class*='name']",
        price_selector="[class*='price']",
        image_selector="img",
    ),
    DomSite(
        name="zuczug", domain="www.zuczug.com", brand_cn="ZUCZUG 素然",
        style_tags=["简约", "生活化时装"], price_band="¥500-8000",
        list_url_tpl="https://www.zuczug.com/list?page={page}",
        item_selector="[class*='product'], [class*='goods'], li.item",
        link_selector="a",
        name_selector="[class*='name'], [class*='title']",
        price_selector="[class*='price']",
        image_selector="img",
    ),
]

# 电商店铺：反爬极强（登录墙/滑块/风控封禁），不在本框架自动采集范围内。
# 替代路径见方案文档：①平台开放联盟 API ②AI Agent 小规模人工监督采集 ③第三方数据服务
PLATFORM_SHOPS: List[PlatformShop] = [
    PlatformShop(
        name="mukzin_tmall", domain="mukzin.tmall.com", brand_cn="密扇 MUKZIN",
        style_tags=["国潮", "潮范中国风"], price_band="¥500-5000",
        note="天猫旗舰店，建议走 AI Agent 辅助或联盟 API",
    ),
    PlatformShop(
        name="exception_tmall", domain="exceptiondm.tmall.com", brand_cn="例外 EXCEPTION",
        style_tags=["东方美学", "非遗工艺"], price_band="¥1000-8000",
        note="官网 mixmind.com 为品牌展示站无商城，商品以天猫旗舰店为主",
    ),
]

ALL_SITES = SHOPIFY_SITES + DOM_SITES + PLATFORM_SHOPS


def get_site(name: str):
    """按名称查找站点配置"""
    for site in ALL_SITES:
        if site.name == name:
            return site
    raise KeyError(f"未找到站点配置: {name}")
