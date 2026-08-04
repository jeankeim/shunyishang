"""
海报生成服务 - 使用 Pillow 在服务端生成高质量海报
支持四种模板：简约风格、五行国潮、社交卡片、宋锦国风
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import List, Dict, Optional
from pathlib import Path
import os
import requests
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 海报尺寸
POSTER_WIDTH = 1080
POSTER_HEIGHT = 1920

# 字体配置（使用系统字体或下载中文字体）
FONT_CONFIG = {
    'title': {'size': 72, 'weight': 'bold'},
    'subtitle': {'size': 36, 'weight': 'normal'},
    'item_name': {'size': 42, 'weight': 'bold'},
    'item_label': {'size': 28, 'weight': 'normal'},
    'footer': {'size': 32, 'weight': 'normal'},
}

# 五行配色主题（与前端 poster-templates.ts 的 WUXING_THEMES 保持一致）
WUXING_THEMES = {
    'fire': {
        'primary': '#FF6B6B',
        'secondary': '#FF8E53',
        'background': '#FAFAF8',
    },
    'wood': {
        'primary': '#4ADE80',
        'secondary': '#22D3EE',
        'background': '#F1F8E9',
    },
    'earth': {
        'primary': '#FCD34D',
        'secondary': '#F59E0B',
        'background': '#FFF8E1',
    },
    'metal': {
        'primary': '#F3F4F6',
        'secondary': '#D1D5DB',
        'background': '#F5F5F5',
    },
    'water': {
        'primary': '#60A5FA',
        'secondary': '#3B82F6',
        'background': '#E3F2FD',
    },
}

# ============================================================
# 宋锦国风模板专用配色（新中式降饱和五色体系）
# ============================================================
GUOFENG_THEMES = {
    'wood':  {'primary': '#4E8560', 'ink_dark': '#33593F', 'ink_light': '#DCE8DC', 'paper': '#F6F3E9'},
    'fire':  {'primary': '#A85D57', 'ink_dark': '#6E3A35', 'ink_light': '#F0DFD8', 'paper': '#F8F1E8'},
    'earth': {'primary': '#9C8654', 'ink_dark': '#6B5A36', 'ink_light': '#EDE3CD', 'paper': '#F8F3E6'},
    'metal': {'primary': '#8FA3AB', 'ink_dark': '#5C6E76', 'ink_light': '#E4EAEC', 'paper': '#F7F5EF'},
    'water': {'primary': '#4F7D9E', 'ink_dark': '#33536B', 'ink_light': '#D9E4EC', 'paper': '#F5F3EA'},
}

SEAL_RED = '#A63D2F'      # 印章朱红
INK = '#2B2B2B'           # 墨色
ANTIQUE_GOLD = '#B08D57'  # 古铜金
INK_GRAY = '#7A7468'      # 纸灰

# 五行传统色（用于五行相生环带）
ELEMENT_TRADITIONAL_COLORS = {
    '木': '#4E8560', '火': '#A85D57', '土': '#9C8654',
    '金': '#8FA3AB', '水': '#3F6C8E',
}

# 主件品类优先级（决定搭配主视觉）
MAIN_CATEGORY_PRIORITY = ['外套', '连衣裙', '裙装', '上装']


def get_font(size: int, weight: str = 'normal') -> ImageFont.FreeTypeFont:
    """获取字体（优先使用系统中文字体）"""
    # 中文字体路径（Linux Docker + macOS + Windows）
    font_paths = [
        # Linux (Docker) - Noto CJK - opentype 目录
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
        # Linux (Docker) - Noto CJK - truetype 目录（备用）
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc',
        # macOS
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
        # Windows
        'C:/Windows/Fonts/msyh.ttc',  # 微软雅黑
        'C:/Windows/Fonts/simsun.ttc',  # 宋体
    ]
    
    logger.info(f"[字体] 开始查找字体，size={size}, weight={weight}")
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, size)
                logger.info(f"[字体] 成功加载: {font_path}")
                return font
            except Exception as e:
                logger.warning(f"[字体] 加载失败 {font_path}: {e}")
                continue
        else:
            logger.debug(f"[字体] 不存在: {font_path}")
    
    # 回退到默认字体（不支持中文）
    logger.error("[字体] 未找到任何中文字体！使用默认字体（中文将显示为方块）")
    logger.error("[字体] 请确保已安装: apt-get install fonts-noto-cjk")
    return ImageFont.load_default()


def download_image(url: str, timeout: int = 15) -> Optional[Image.Image]:
    """下载图片并返回 PIL Image 对象（带重试）"""
    try:
        # 处理相对路径
        if url.startswith('/'):
            # 检查是否是 seed 图片（在前端 public 目录）
            if '/images/seed/' in url:
                # 从文件系统直接读取
                project_root = Path(__file__).parent.parent.parent.parent
                image_path = project_root / "apps" / "web" / "public" / url.lstrip('/')
                
                if image_path.exists():
                    logger.info(f"从文件系统加载图片: {image_path}")
                    return Image.open(image_path).convert('RGBA')
                else:
                    logger.warning(f"图片文件不存在: {image_path}")
                    return None
            
            # 检查是否是 uploads 图片（用户上传的衣物）
            elif '/uploads/wardrobe/' in url:
                # 从文件系统直接读取
                # uploads 目录在 data/uploads/wardrobe/
                project_root = Path(__file__).parent.parent.parent.parent
                # URL 路径去掉前导 /
                url_path = url.lstrip('/')
                image_path = project_root / "data" / url_path
                
                if image_path.exists():
                    logger.info(f"从文件系统加载衣物图片: {image_path}")
                    return Image.open(image_path).convert('RGBA')
                else:
                    logger.warning(f"衣物图片文件不存在: {image_path}")
                    return None
            
            # 其他相对路径，尝试从后端 uploads 目录
            base_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
            url = f"{base_url}{url}"
        
        # HTTP 下载（带重试，最多 2 次）
        for attempt in range(2):
            try:
                logger.info(f"下载图片(尝试{attempt+1}): {url}")
                response = requests.get(url, timeout=timeout, stream=False)
                response.raise_for_status()
                return Image.open(BytesIO(response.content)).convert('RGBA')
            except (requests.Timeout, requests.ConnectionError) as e:
                if attempt == 0:
                    logger.warning(f"下载超时/连接失败，重试: {url}")
                    continue
                raise
    except Exception as e:
        logger.error(f"下载图片失败: {url}, 错误: {e}")
        return None


def create_gradient_background(width: int, height: int, color1: str, color2: str) -> Image.Image:
    """创建渐变背景"""
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    # 解析颜色
    c1 = tuple(int(color1[i:i+2], 16) for i in (1, 3, 5))
    c2 = tuple(int(color2[i:i+2], 16) for i in (1, 3, 5))
    
    # 绘制垂直渐变
    for y in range(height):
        r = int(c1[0] + (c2[0] - c1[0]) * y / height)
        g = int(c1[1] + (c2[1] - c1[1]) * y / height)
        b = int(c1[2] + (c2[2] - c1[2]) * y / height)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return img


def get_serif_font(size: int) -> ImageFont.FreeTypeFont:
    """获取宋体/衬线字体（国风模板专用，找不到时回退黑体）"""
    serif_paths = [
        '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc',
        '/System/Library/Fonts/Supplemental/Songti.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        'C:/Windows/Fonts/simsun.ttc',
    ]
    for font_path in serif_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    # 回退到系统字体查找链（黑体）
    return get_font(size)


def hex_to_rgb(color: str) -> tuple:
    """'#RRGGBB' -> (r, g, b)"""
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> List[str]:
    """按像素宽度对文本折行（逐字符，适配中文）"""
    lines: List[str] = []
    line = ''
    for ch in text:
        if draw.textlength(line + ch, font=font) <= max_width:
            line += ch
        else:
            if line:
                lines.append(line)
            line = ch
    if line:
        lines.append(line)
    return lines


def draw_meander(draw: ImageDraw.ImageDraw, x0: int, y0: int, width: int,
                 unit: int = 30, color=ANTIQUE_GOLD, line_width: int = 3):
    """绘制回纹装饰带（矩形回旋纹，逐单元重复）"""
    h = int(unit * 0.72)
    x = x0
    while x + unit <= x0 + width:
        pts = [
            (x, y0 + h), (x, y0), (x + unit, y0), (x + unit, y0 + h),
            (x + unit * 0.32, y0 + h), (x + unit * 0.32, y0 + h * 0.42),
            (x + unit * 0.68, y0 + h * 0.42), (x + unit * 0.68, y0 + h * 0.74),
        ]
        draw.line(pts, fill=color, width=line_width, joint='curve')
        x += unit


def draw_seal(draw: ImageDraw.ImageDraw, x: int, y: int, size: int,
              text: str, font=None, fill: str = SEAL_RED):
    """绘制印章（圆角方块 + 白色衬线字）"""
    draw.rounded_rectangle([x, y, x + size, y + size], radius=size // 10, fill=fill)
    seal_font = font or get_serif_font(int(size * 0.5))
    draw.text((x + size // 2, y + size // 2), text, fill='#FFFFFF',
              font=seal_font, anchor='mm')


def get_lunar_date_str() -> str:
    """获取农历日期（如「丙午年六月二十」），失败返回空串"""
    try:
        import cnlunar
        lunar = cnlunar.Lunar(datetime.now(), godType='8char')
        # year8Char 为干支纪年；lunarMonthCn 含「大/小」月标记需剔除
        month = lunar.lunarMonthCn.replace('大', '').replace('小', '')
        return f"{lunar.year8Char}年{month}{lunar.lunarDayCn}"
    except Exception as e:
        logger.warning(f"[Poster] 农历解析失败: {e}")
        return ''


def pick_main_item_index(items: List[Dict]) -> int:
    """按品类优先级选出搭配主件（外套/连衣裙/裙装/上装 优先）"""
    for cat in MAIN_CATEGORY_PRIORITY:
        for i, item in enumerate(items):
            if (item.get('category') or '') == cat:
                return i
    return 0


def generate_simple_poster(
    title: str,
    items: List[Dict],
    xiyong_elements: List[str],
    theme_name: str = 'fire',
    quote: str = '',
    signature: str = '顺衣尚',
    scene: str = '',
) -> Image.Image:
    """生成简约风格海报"""
    theme = WUXING_THEMES.get(theme_name, WUXING_THEMES['fire'])
    
    # 创建背景
    img = Image.new('RGB', (POSTER_WIDTH, POSTER_HEIGHT), theme['background'])
    draw = ImageDraw.Draw(img)
    
    # 顶部装饰线
    draw.rectangle([0, 0, POSTER_WIDTH, 12], fill=theme['primary'])
    
    # 标题
    title_font = get_font(FONT_CONFIG['title']['size'], 'bold')
    title_y = 80
    draw.text((POSTER_WIDTH // 2, title_y), title, fill='#1A1A1A', font=title_font, anchor='mm')
    
    # 引言
    if quote:
        quote_font = get_font(FONT_CONFIG['subtitle']['size'])
        quote_y = title_y + 100
        draw.text((POSTER_WIDTH // 2, quote_y), f'"{quote}"', fill='#4A4A4A', font=quote_font, anchor='mm')
    
    # 装饰线
    deco_y = title_y + 180 if quote else title_y + 120
    draw.line([(200, deco_y), (POSTER_WIDTH - 200, deco_y)], fill='#E5E7EB', width=2)
    draw.rectangle([POSTER_WIDTH // 2 - 8, deco_y - 8, POSTER_WIDTH // 2 + 8, deco_y + 8], fill=theme['primary'])
    
    # 穿搭列表
    item_start_y = deco_y + 100
    item_height = 200
    item_spacing = 30
    
    for i, item in enumerate(items[:5]):
        y = item_start_y + i * (item_height + item_spacing)
        
        # 卡片背景
        card_x = 80
        card_y = y
        card_width = POSTER_WIDTH - 160
        card_height = item_height
        
        # 圆角矩形卡片
        radius = 24
        # Pillow 不支持 rgba，使用 RGBA 元组
        draw.rounded_rectangle(
            [card_x, card_y, card_x + card_width, card_y + card_height],
            radius=radius,
            fill=(255, 255, 255, 204),  # rgba(255, 255, 255, 0.8)
            outline=(0, 0, 0, 15),  # rgba(0, 0, 0, 0.06)
            width=2,
        )
        
        # 序号圆圈
        circle_x = card_x + 60
        circle_y = card_y + card_height // 2
        draw.ellipse(
            [circle_x - 40, circle_y - 40, circle_x + 40, circle_y + 40],
            fill=theme['primary'],
        )
        num_font = get_font(36, 'bold')
        draw.text((circle_x, circle_y), str(i + 1), fill='white', font=num_font, anchor='mm')
        
        # 图片
        if item.get('image_url'):
            item_img = download_image(item['image_url'])
            if item_img:
                # 缩放到 160x160
                item_img = item_img.resize((160, 160), Image.Resampling.LANCZOS)
                img.paste(item_img, (card_x + 140, card_y + 40), item_img)
        
        # 物品名称
        name_font = get_font(FONT_CONFIG['item_name']['size'], 'bold')
        name_x = card_x + 340
        name_y = card_y + 60
        draw.text((name_x, name_y), item['name'], fill='#1A1A1A', font=name_font, anchor='lm')
        
        # 五行标签
        if item.get('primary_element'):
            label_font = get_font(FONT_CONFIG['item_label']['size'])
            label_y = name_y + 60
            draw.text((name_x, label_y), item['primary_element'], fill=theme['secondary'], font=label_font, anchor='lm')
    
    # 底部信息
    footer_y = POSTER_HEIGHT - 200
    draw.line([(80, footer_y), (POSTER_WIDTH - 80, footer_y)], fill=(0, 0, 0, 20), width=2)  # rgba(0,0,0,0.08)
    
    # 喜用神
    if xiyong_elements:
        footer_font = get_font(FONT_CONFIG['footer']['size'])
        footer_x = 100
        footer_y += 50
        draw.text((footer_x, footer_y), '喜用神', fill='#6B7280', font=footer_font, anchor='lm')
        
        # 标签
        tag_x = footer_x + 160
        for element in xiyong_elements:
            tag_width = 100
            tag_height = 50
            draw.rounded_rectangle(
                [tag_x, footer_y - 25, tag_x + tag_width, footer_y + 25],
                radius=12,
                fill=theme['primary'],
            )
            tag_font = get_font(28, 'bold')
            draw.text((tag_x + tag_width // 2, footer_y), element, fill='white', font=tag_font, anchor='mm')
            tag_x += tag_width + 20
    
    # 签名
    sign_font = get_font(32)
    draw.text((POSTER_WIDTH - 100, POSTER_HEIGHT - 80), f'—— {signature}', fill='#6B7280', font=sign_font, anchor='rm')
    
    # 底部引导文字（独立一行，小号字体）
    guide_font = get_font(20)
    draw.text((POSTER_WIDTH // 2, POSTER_HEIGHT - 35), '扫码登录 shunyishang.com 体验更多功能', fill='#9CA3AF', font=guide_font, anchor='mm')
    
    return img


def generate_wuxing_poster(
    title: str,
    items: List[Dict],
    xiyong_elements: List[str],
    theme_name: str = 'fire',
    quote: str = '',
    signature: str = '顺衣尚',
    scene: str = '',
) -> Image.Image:
    """生成五行国潮风格海报"""
    theme = WUXING_THEMES.get(theme_name, WUXING_THEMES['fire'])
    
    # 创建深色渐变背景
    img = Image.new('RGB', (POSTER_WIDTH, POSTER_HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # 绘制深蓝渐变背景
    for y in range(POSTER_HEIGHT):
        ratio = y / POSTER_HEIGHT
        r = int(26 + (15 - 26) * ratio)
        g = int(26 + (33 - 26) * ratio)
        b = int(46 + (96 - 46) * ratio)
        draw.line([(0, y), (POSTER_WIDTH, y)], fill=(r, g, b))
    
    # 顶部五行印章设计
    circle_x = POSTER_WIDTH // 2
    circle_y = 100
    circle_radius = 50
    
    # 外圈装饰环（更细更淡）
    draw.ellipse(
        [circle_x - circle_radius - 8, circle_y - circle_radius - 8,
         circle_x + circle_radius + 8, circle_y + circle_radius + 8],
        outline=theme['primary'],
        width=2,
    )
    
    # 主圆圈
    draw.ellipse(
        [circle_x - circle_radius, circle_y - circle_radius,
         circle_x + circle_radius, circle_y + circle_radius],
        fill=theme['primary'],
    )
    
    # 五行文字
    element_font = get_font(48, 'bold')
    element_text = xiyong_elements[0] if xiyong_elements else '五行'
    draw.text((circle_x, circle_y), element_text, fill='white', font=element_font, anchor='mm')
    
    # 装饰线（更精致）
    deco_y = circle_y + circle_radius + 30
    draw.line([(POSTER_WIDTH // 2 - 200, deco_y), (POSTER_WIDTH // 2 + 200, deco_y)], fill=(255, 255, 255, 50), width=1)
    # 中心点缀
    draw.rectangle(
        [POSTER_WIDTH // 2 - 6, deco_y - 6, POSTER_WIDTH // 2 + 6, deco_y + 6],
        fill=theme['primary'],
    )
    
    # 标题
    title_font = get_font(FONT_CONFIG['title']['size'], 'bold')
    title_y = 220
    draw.text((POSTER_WIDTH // 2, title_y), title, fill='white', font=title_font, anchor='mm')
    
    # 装饰线
    deco_y = title_y + 60
    draw.line([(300, deco_y), (POSTER_WIDTH - 300, deco_y)], fill=(255, 255, 255, 76), width=2)  # rgba(255,255,255,0.3)
    draw.rectangle([POSTER_WIDTH // 2 - 8, deco_y - 8, POSTER_WIDTH // 2 + 8, deco_y + 8], fill=theme['primary'])
    
    # 副标题
    subtitle_font = get_font(FONT_CONFIG['subtitle']['size'])
    subtitle_y = deco_y + 50
    draw.text((POSTER_WIDTH // 2, subtitle_y), '五行相生 · 运势亨通', fill=(255, 255, 255, 204), font=subtitle_font, anchor='mm')  # rgba(255,255,255,0.8)
    
    # 穿搭列表
    item_start_y = subtitle_y + 80
    item_height = 180
    item_spacing = 25
    
    for i, item in enumerate(items[:5]):
        y = item_start_y + i * (item_height + item_spacing)
        
        # 卡片背景（半透明深色）
        card_x = 80
        card_y = y
        card_width = POSTER_WIDTH - 160
        card_height = item_height
        
        # 圆角矩形卡片 - 不使用 fill，只用边框
        radius = 20
        # 绘制边框（不使用填充，避免纯白色）
        draw.rounded_rectangle(
            [card_x, card_y, card_x + card_width, card_y + card_height],
            radius=radius,
            outline=(255, 255, 255, 50),  # 淡淡的白色边框
            width=2,
        )
        
        # 序号方块
        square_x = card_x + 50
        square_y = card_y + card_height // 2
        draw.rounded_rectangle(
            [square_x - 25, square_y - 25, square_x + 25, square_y + 25],
            radius=8,
            fill=theme['primary'],
        )
        num_font = get_font(28, 'bold')
        draw.text((square_x, square_y), str(i + 1), fill='white', font=num_font, anchor='mm')
        
        # 图片
        if item.get('image_url'):
            item_img = download_image(item['image_url'])
            if item_img:
                item_img = item_img.resize((160, 160), Image.Resampling.LANCZOS)
                img.paste(item_img, (card_x + 120, card_y + 35), item_img)
        
        # 物品名称（白色文字）
        name_font = get_font(FONT_CONFIG['item_name']['size'], 'bold')
        name_x = card_x + 320
        name_y = card_y + 50
        draw.text((name_x, name_y), item['name'], fill='white', font=name_font, anchor='lm')
        
        # 颜色标签
        if item.get('color'):
            color_font = get_font(FONT_CONFIG['item_label']['size'])
            color_y = name_y + 50
            draw.text((name_x, color_y), item['color'], fill=(255, 255, 255, 180), font=color_font, anchor='lm')
        
        # 五行标签
        if item.get('primary_element'):
            label_font = get_font(FONT_CONFIG['item_label']['size'])
            label_x = name_x + 120 if item.get('color') else name_x
            label_y = name_y + 50
            draw.text((label_x, label_y), item['primary_element'], fill=theme['secondary'], font=label_font, anchor='lm')
    
    # 底部品牌区（分行布局，避免重叠）
    footer_y = POSTER_HEIGHT - 160
    
    # 分隔线
    draw.line([(80, footer_y), (POSTER_WIDTH - 80, footer_y)], fill=(255, 255, 255, 25), width=2)
    
    # 第一行：左侧品牌 + 右侧生成时间
    row1_y = footer_y + 45
    
    # 品牌图标
    brand_x = 100
    draw.rounded_rectangle(
        [brand_x, row1_y - 18, brand_x + 36, row1_y + 18],
        radius=8,
        fill=theme['primary'],
    )
    brand_icon_font = get_font(18, 'bold')
    draw.text((brand_x + 18, row1_y), '五行', fill='white', font=brand_icon_font, anchor='mm')
    
    # 品牌名称
    brand_font = get_font(26, 'bold')
    draw.text((brand_x + 50, row1_y), '顺衣尚', fill='white', font=brand_font, anchor='lm')
    
    # 右侧生成时间
    from datetime import datetime
    current_time = datetime.now().strftime('%H:%M:%S')
    time_font = get_font(22)
    draw.text((POSTER_WIDTH - 100, row1_y), f'生成时间：{current_time}', fill=(255, 255, 255, 153), font=time_font, anchor='rm')
    
    # 第二行：品牌副标题（居中，小号字体）
    row2_y = row1_y + 40
    brand_sub_font = get_font(20)
    draw.text((POSTER_WIDTH // 2, row2_y), '传统智慧 · 现代穿搭', fill=(255, 255, 255, 100), font=brand_sub_font, anchor='mm')
    
    # 第三行：引导文字（居中，小号字体）
    row3_y = row2_y + 35
    guide_font = get_font(20)
    draw.text((POSTER_WIDTH // 2, row3_y), '扫码登录 shunyishang.com 体验更多功能', fill=(255, 255, 255, 80), font=guide_font, anchor='mm')
    
    # 第四行：签名（右下角）
    sign_font = get_font(24, 'bold')
    draw.text((POSTER_WIDTH - 100, row3_y + 35), '—— 顺衣尚', fill=(255, 255, 255, 153), font=sign_font, anchor='rm')
    
    return img


def generate_card_poster(
    title: str,
    items: List[Dict],
    xiyong_elements: List[str],
    theme_name: str = 'fire',
    quote: str = '',
    signature: str = '顺衣尚',
    scene: str = '',
    username: str = '',
) -> Image.Image:
    """生成社交卡片风格海报"""
    theme = WUXING_THEMES.get(theme_name, WUXING_THEMES['fire'])
    
    # 创建浅灰渐变背景
    img = Image.new('RGB', (POSTER_WIDTH, POSTER_HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # 绘制浅灰渐变
    for y in range(POSTER_HEIGHT):
        ratio = y / POSTER_HEIGHT
        r = int(248 + (233 - 248) * ratio)
        g = int(249 + (236 - 249) * ratio)
        b = int(250 + (239 - 250) * ratio)
        draw.line([(0, y), (POSTER_WIDTH, y)], fill=(r, g, b))
    
    # 用户信息头部
    header_y = 60
    header_height = 100
    header_x = 80
    header_width = POSTER_WIDTH - 160
    
    # 卡片背景
    draw.rounded_rectangle(
        [header_x, header_y, header_x + header_width, header_y + header_height],
        radius=24,
        fill=(255, 255, 255, 204),  # rgba(255,255,255,0.8)
        outline=(0, 0, 0, 15),
        width=2,
    )
    
    # 用户头像圆圈（显示用户名首字）
    avatar_x = header_x + 70
    avatar_y = header_y + header_height // 2
    draw.ellipse(
        [avatar_x - 35, avatar_y - 35, avatar_x + 35, avatar_y + 35],
        fill=theme['primary'],
    )
    avatar_font = get_font(36, 'bold')
    avatar_char = (username or 'U')[0].upper()
    draw.text((avatar_x, avatar_y), avatar_char, fill='white', font=avatar_font, anchor='mm')
    
    # 用户名
    display_name = username or '用户'
    name_font = get_font(32, 'bold')
    draw.text((avatar_x + 70, avatar_y - 15), f'@{display_name}', fill='#212529', font=name_font, anchor='lm')
    
    # 发布时间
    time_font = get_font(24)
    draw.text((avatar_x + 70, avatar_y + 20), '刚刚发布 · 五行穿搭', fill='#6B7280', font=time_font, anchor='lm')
    
    # 标题
    title_font = get_font(48, 'bold')
    title_y = header_y + header_height + 60
    draw.text((100, title_y), title, fill='#212529', font=title_font, anchor='lm')
    
    # 场景标签
    if scene:
        scene_font = get_font(28)
        scene_y = title_y + 60
        draw.text((100, scene_y), f'🎯 {scene}', fill='#6B7280', font=scene_font, anchor='lm')
    
    # 单品网格（2x2）
    grid_start_y = scene_y + 100 if scene else title_y + 100
    grid_item_width = 440
    grid_item_height = 380
    grid_gap = 24
        
    for i, item in enumerate(items[:4]):
        row = i // 2
        col = i % 2
            
        item_x = 80 + col * (grid_item_width + grid_gap)
        item_y = grid_start_y + row * (grid_item_height + grid_gap)
            
        # 卡片背景
        draw.rounded_rectangle(
            [item_x, item_y, item_x + grid_item_width, item_y + grid_item_height],
            radius=24,
            fill='white',
            outline=(0, 0, 0, 15),
            width=2,
        )
            
        # 图片区域（4:3 比例，避免纵向压缩）
        img_area_height = 300
        if item.get('image_url'):
            item_img = download_image(item['image_url'])
            if item_img:
                # 保持宽高比裁剪：先缩放到宽度匹配，再居中裁剪高度
                orig_w, orig_h = item_img.size
                target_ratio = grid_item_width / img_area_height
                orig_ratio = orig_w / orig_h
                if orig_ratio > target_ratio:
                    # 原图更宽，按高度缩放后裁左右
                    new_h = img_area_height
                    new_w = int(orig_w * new_h / orig_h)
                    item_img = item_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    left = (new_w - grid_item_width) // 2
                    item_img = item_img.crop((left, 0, left + grid_item_width, new_h))
                else:
                    # 原图更高，按宽度缩放后裁上下
                    new_w = grid_item_width
                    new_h = int(orig_h * new_w / orig_w)
                    item_img = item_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    top = (new_h - img_area_height) // 2
                    item_img = item_img.crop((0, top, new_w, top + img_area_height))
                img.paste(item_img, (item_x, item_y), item_img)
            
        # 序号标签
        num_bg_x = item_x + 16
        num_bg_y = item_y + 16
        draw.rounded_rectangle(
            [num_bg_x, num_bg_y, num_bg_x + 44, num_bg_y + 44],
            radius=22,
            fill=theme['primary'],
        )
        num_font = get_font(26, 'bold')
        draw.text((num_bg_x + 22, num_bg_y + 22), str(i + 1), fill='white', font=num_font, anchor='mm')
            
        # 物品名称
        name_y = item_y + img_area_height + 24
        name_font = get_font(30, 'bold')
        draw.text((item_x + 20, name_y), item['name'], fill='#212529', font=name_font, anchor='lm')
            
        # 五行标签
        if item.get('primary_element'):
            tag_x = item_x + 20
            tag_y = name_y + 50
            draw.rounded_rectangle(
                [tag_x, tag_y - 18, tag_x + 70, tag_y + 18],
                radius=18,
                fill=theme['primary'],
            )
            tag_font = get_font(24)
            draw.text((tag_x + 35, tag_y), item['primary_element'], fill='white', font=tag_font, anchor='mm')
        
    # 标签区域（移除假的互动数据）
    interaction_y = grid_start_y + 2 * (grid_item_height + grid_gap) + 40
    draw.rounded_rectangle(
        [80, interaction_y, POSTER_WIDTH - 80, interaction_y + 120],
        radius=24,
        fill=(255, 255, 255, 204),
        outline=(0, 0, 0, 15),
        width=2,
    )
        
    # 五行标签
    tag_start_x = 120
    tag_y = interaction_y + 60
    for element in xiyong_elements:
        tag_width = 160
        draw.rounded_rectangle(
            [tag_start_x, tag_y - 22, tag_start_x + tag_width, tag_y + 22],
            radius=22,
            fill=theme['primary'],
        )
        tag_font = get_font(26, 'bold')
        draw.text((tag_start_x + tag_width // 2, tag_y), f'#{element}穿搭', fill='white', font=tag_font, anchor='mm')
        tag_start_x += tag_width + 20
        
    # 底部品牌标识（分行布局）
    footer_y = POSTER_HEIGHT - 120
    draw.line([(80, footer_y), (POSTER_WIDTH - 80, footer_y)], fill=(0, 0, 0, 20), width=2)
    
    # 第一行：品牌 + 日期
    row1_y = footer_y + 40
    brand_font = get_font(26, 'bold')
    draw.text((100, row1_y), '顺衣尚', fill='#6B7280', font=brand_font, anchor='lm')
        
    date_font = get_font(24)
    from datetime import datetime
    draw.text((POSTER_WIDTH - 100, row1_y), datetime.now().strftime('%Y-%m-%d'), fill='#9CA3AF', font=date_font, anchor='rm')
        
    # 第二行：引导文字（居中，小号字体，独立一行）
    guide_font = get_font(20)
    draw.text((POSTER_WIDTH // 2, row1_y + 38), '扫码登录 shunyishang.com 体验更多功能', fill='#9CA3AF', font=guide_font, anchor='mm')
    
    return img


def generate_guofeng_poster(
    title: str,
    items: List[Dict],
    xiyong_elements: List[str],
    theme_name: str = 'fire',
    quote: str = '',
    signature: str = '顺衣尚',
    scene: str = '',
    username: str = '',
) -> Image.Image:
    """
    生成「宋锦国风」海报：宣纸底 + 水墨晕染 + 印章/回纹/衬线字，
    完整展示整套搭配（主件大视觉 + 分类单品清单 + 五行相生环带）
    """
    theme = GUOFENG_THEMES.get(theme_name, GUOFENG_THEMES['fire'])
    primary = hex_to_rgb(theme['primary'])
    ink_dark = hex_to_rgb(theme['ink_dark'])

    # ---- 背景：宣纸色 + 水墨晕染 ----
    img = Image.new('RGB', (POSTER_WIDTH, POSTER_HEIGHT), theme['paper'])
    overlay = Image.new('RGBA', (POSTER_WIDTH, POSTER_HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([-200, -260, 620, 320], fill=(*ink_dark, 55))
    od.ellipse([700, -200, 1400, 260], fill=(*primary, 45))
    od.ellipse([-300, 1650, 500, 2200], fill=(*primary, 28))
    od.ellipse([760, 1700, 1400, 2250], fill=(*ink_dark, 28))
    overlay = overlay.filter(ImageFilter.GaussianBlur(90))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)

    # ---- 顶部回纹装饰带 ----
    draw_meander(draw, 90, 44, POSTER_WIDTH - 180, unit=30, color=ANTIQUE_GOLD, line_width=2)

    # ---- 左上印章（喜用神首字）----
    seal_char = xiyong_elements[0] if xiyong_elements else '衣'
    draw_seal(draw, 90, 96, 104, seal_char, font=get_serif_font(52))

    # ---- 右侧竖排农历日期 ----
    lunar = get_lunar_date_str()
    if lunar:
        v_font = get_serif_font(26)
        for i, ch in enumerate(lunar):
            draw.text((POSTER_WIDTH - 118, 104 + i * 36), ch, fill=INK_GRAY, font=v_font, anchor='mm')

    # ---- 主标题（衬线大字）----
    title_font = get_serif_font(76)
    draw.text((POSTER_WIDTH // 2, 300), title, fill=INK, font=title_font, anchor='mm')

    # ---- 装饰分隔（两侧细线 + 中央菱形）----
    deco_y = 378
    draw.line([(240, deco_y), (470, deco_y)], fill=ANTIQUE_GOLD, width=2)
    draw.line([(610, deco_y), (840, deco_y)], fill=ANTIQUE_GOLD, width=2)
    draw.polygon([(540, deco_y - 10), (550, deco_y), (540, deco_y + 10), (530, deco_y)], fill=theme['primary'])

    # ---- 副标题 ----
    sub_font = get_serif_font(32)
    draw.text((POSTER_WIDTH // 2, 430), '五行相生 · 顺势而衣', fill=theme['primary'], font=sub_font, anchor='mm')

    # ---- 搭配哲理引言（物品较多时省略以保完整展示）----
    visible_items = items[:6]
    y = 486
    if quote and len(visible_items) <= 4:
        quote_font = get_serif_font(28)
        quote_lines = wrap_text(draw, quote, quote_font, POSTER_WIDTH - 300)[:2]
        # 两侧古铜金竖线
        draw.line([(130, y + 4), (130, y + len(quote_lines) * 44 + 8)], fill=ANTIQUE_GOLD, width=3)
        draw.line([(POSTER_WIDTH - 130, y + 4), (POSTER_WIDTH - 130, y + len(quote_lines) * 44 + 8)], fill=ANTIQUE_GOLD, width=3)
        for i, line in enumerate(quote_lines):
            draw.text((POSTER_WIDTH // 2, y + 20 + i * 44), line, fill='#4A4438', font=quote_font, anchor='mm')
        y += len(quote_lines) * 44 + 40

    # ---- 衣单区标题 ----
    section_font = get_serif_font(28)
    section_text = f'· {username} 的今日衣单 ·' if username else '· 今日衣单 ·'
    draw.text((POSTER_WIDTH // 2, y + 14), section_text, fill=ANTIQUE_GOLD, font=section_font, anchor='mm')
    y += 50

    # ---- 主件大视觉 + 右侧信息 ----
    if visible_items:
        main_idx = pick_main_item_index(visible_items)
        hero = visible_items[main_idx]
        rest = [it for i, it in enumerate(visible_items) if i != main_idx]
        hero_size = 360 if len(visible_items) >= 5 else 400
        hero_x, hero_y = 90, y

        if hero.get('image_url'):
            hero_img = download_image(hero['image_url'])
            if hero_img:
                # 保比例居中裁剪为正方形
                w, h = hero_img.size
                side = min(w, h)
                hero_img = hero_img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
                hero_img = hero_img.resize((hero_size - 16, hero_size - 16), Image.Resampling.LANCZOS)
                img.paste(hero_img, (hero_x + 8, hero_y + 8), hero_img)
                draw = ImageDraw.Draw(img)
        # 双重边框：外层古铜金 + 内层主题色
        draw.rounded_rectangle([hero_x, hero_y, hero_x + hero_size, hero_y + hero_size],
                               radius=16, outline=ANTIQUE_GOLD, width=3)
        draw.rounded_rectangle([hero_x + 10, hero_y + 10, hero_x + hero_size - 10, hero_y + hero_size - 10],
                               radius=10, outline=theme['primary'], width=1)

        # 右侧信息列
        info_x = hero_x + hero_size + 48
        info_w = POSTER_WIDTH - 90 - info_x
        info_y = hero_y + 16

        name_font = get_serif_font(36)
        name_lines = wrap_text(draw, hero.get('name', ''), name_font, info_w)[:2]
        for i, line in enumerate(name_lines):
            draw.text((info_x, info_y + i * 48), line, fill=INK, font=name_font, anchor='lm')
        info_y += len(name_lines) * 48 + 16

        # 五行小印章 + 品类标签
        if hero.get('primary_element'):
            draw_seal(draw, info_x, info_y - 20, 44, hero['primary_element'], font=get_serif_font(24))
        cat = hero.get('category')
        if cat:
            cat_font = get_serif_font(24)
            cat_x = info_x + (58 if hero.get('primary_element') else 0)
            cat_w = int(draw.textlength(cat, font=cat_font)) + 36
            draw.rounded_rectangle([cat_x, info_y - 18, cat_x + cat_w, info_y + 26],
                                   radius=6, outline=ANTIQUE_GOLD, width=2)
            draw.text((cat_x + cat_w // 2, info_y + 4), cat, fill=INK_GRAY, font=cat_font, anchor='mm')
        info_y += 60

        # 推荐理由
        if hero.get('reason'):
            reason_font = get_serif_font(24)
            reason_lines = wrap_text(draw, hero['reason'], reason_font, info_w)[:3]
            for i, line in enumerate(reason_lines):
                draw.text((info_x, info_y + i * 38), line, fill=INK_GRAY, font=reason_font, anchor='lm')
        y += hero_size + 34

        # ---- 其余单品清单（全量展示，最多 5 件）----
        row_font_name = get_serif_font(28)
        row_font_sub = get_serif_font(21)
        for sub in rest[:5]:
            # 卡片底
            draw.rounded_rectangle([90, y, POSTER_WIDTH - 90, y + 112],
                                   radius=14, fill='#FFFDF6', outline=(176, 141, 87, 120), width=2)
            # 图片
            if sub.get('image_url'):
                sub_img = download_image(sub['image_url'])
                if sub_img:
                    w, h = sub_img.size
                    side = min(w, h)
                    sub_img = sub_img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
                    sub_img = sub_img.resize((92, 92), Image.Resampling.LANCZOS)
                    img.paste(sub_img, (112, y + 10), sub_img)
                    draw = ImageDraw.Draw(img)

            # 名称（单行省略）
            name = sub.get('name', '')
            while name and draw.textlength(name, font=row_font_name) > 430:
                name = name[:-1]
            if name != sub.get('name', ''):
                name += '…'
            draw.text((228, y + 34), name, fill=INK, font=row_font_name, anchor='lm')

            # 副信息：品类 · 推荐理由节选
            sub_parts = []
            if sub.get('category'):
                sub_parts.append(sub['category'])
            if sub.get('reason'):
                sub_parts.append(sub['reason'][:16])
            if sub_parts:
                draw.text((228, y + 78), ' · '.join(sub_parts), fill=INK_GRAY, font=row_font_sub, anchor='lm')

            # 右侧五行小印章
            if sub.get('primary_element'):
                draw_seal(draw, POSTER_WIDTH - 160, y + 36, 40, sub['primary_element'], font=get_serif_font(22))
            y += 124

    # ---- 五行相生环带 ----
    band_y = min(y + 20, 1540)
    band_caption_font = get_serif_font(24)
    draw.text((POSTER_WIDTH // 2, band_y), '五行相生 · 生生不息', fill=ANTIQUE_GOLD, font=band_caption_font, anchor='mm')

    element_order = ['木', '火', '土', '金', '水']
    active_elements = set(xiyong_elements)
    for it in visible_items:
        if it.get('primary_element'):
            active_elements.add(it['primary_element'])

    cy = band_y + 70
    centers_x = [180, 360, 540, 720, 900]
    r = 38
    elem_font = get_serif_font(32)
    tiny_font = get_serif_font(18)
    for i, elem in enumerate(element_order):
        cx = centers_x[i]
        if i < len(element_order) - 1:
            # 相生连线 + 「生」字
            draw.line([(cx + r + 8, cy), (centers_x[i + 1] - r - 8, cy)], fill='#B5AEA0', width=2)
            draw.text(((cx + centers_x[i + 1]) // 2, cy - 22), '生', fill='#B5AEA0', font=tiny_font, anchor='mm')
        if elem in active_elements:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ELEMENT_TRADITIONAL_COLORS[elem])
            draw.text((cx, cy), elem, fill='#FFFFFF', font=elem_font, anchor='mm')
        else:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline='#C9C2B4', width=2)
            draw.text((cx, cy), elem, fill='#B5AEA0', font=elem_font, anchor='mm')

    # ---- 底部品牌区 ----
    draw_meander(draw, 120, 1712, POSTER_WIDTH - 240, unit=26, color=ANTIQUE_GOLD, line_width=2)

    # 品牌印章 + 名称（左），日期（右）
    draw_seal(draw, 100, 1762, 52, '顺', font=get_serif_font(28))
    brand_font = get_serif_font(30)
    draw.text((168, 1788), '顺衣尚 · 五行穿搭', fill=INK, font=brand_font, anchor='lm')
    date_font = get_serif_font(22)
    date_str = datetime.now().strftime('%Y-%m-%d')
    if lunar:
        date_str += f' · {lunar}'
    draw.text((POSTER_WIDTH - 100, 1788), date_str, fill=INK_GRAY, font=date_font, anchor='rm')

    slogan_font = get_serif_font(24)
    draw.text((POSTER_WIDTH // 2, 1848), '传统智慧 · 现代穿搭', fill=INK_GRAY, font=slogan_font, anchor='mm')
    guide_font = get_serif_font(22)
    draw.text((POSTER_WIDTH // 2, 1888), '扫码登录 shunyishang.com 领取专属五行穿搭',
              fill=INK_GRAY, font=guide_font, anchor='mm')

    return img


def generate_poster(
    layout: str = 'simple',
    title: str = '今日五行穿搭推荐',
    items: List[Dict] = None,
    xiyong_elements: List[str] = None,
    theme: str = 'fire',
    quote: str = '',
    signature: str = '顺衣尚',
    scene: str = '',
    username: str = '',
) -> bytes:
    """
    生成海报图片
    
    Args:
        layout: 模板布局 (simple/wuxing/card)
        title: 海报标题
        items: 穿搭物品列表
        xiyong_elements: 喜用神元素
        theme: 五行主题 (fire/wood/earth/metal/water)
        quote: 引言
        signature: 签名
        scene: 场景
        username: 用户名（卡片模板使用）
    
    Returns:
        图片字节数据 (PNG)
    """
    items = items or []
    xiyong_elements = xiyong_elements or []
    
    try:
        # 根据布局选择生成函数
        if layout == 'simple':
            img = generate_simple_poster(
                title=title,
                items=items,
                xiyong_elements=xiyong_elements,
                theme_name=theme,
                quote=quote,
                signature=signature,
                scene=scene,
            )
        elif layout == 'guofeng':
            img = generate_guofeng_poster(
                title=title,
                items=items,
                xiyong_elements=xiyong_elements,
                theme_name=theme,
                quote=quote,
                signature=signature,
                scene=scene,
                username=username,
            )
        elif layout == 'wuxing':
            img = generate_wuxing_poster(
                title=title,
                items=items,
                xiyong_elements=xiyong_elements,
                theme_name=theme,
                quote=quote,
                signature=signature,
                scene=scene,
            )
        elif layout == 'card':
            img = generate_card_poster(
                title=title,
                items=items,
                xiyong_elements=xiyong_elements,
                theme_name=theme,
                quote=quote,
                signature=signature,
                scene=scene,
                username=username,
            )
        else:
            img = generate_simple_poster(
                title=title,
                items=items,
                xiyong_elements=xiyong_elements,
                theme_name=theme,
                quote=quote,
                signature=signature,
                scene=scene,
            )
        
        # 转换为 PNG 字节数据
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr.seek(0)
        
        logger.info(f"海报生成成功: {title}, 尺寸: {POSTER_WIDTH}x{POSTER_HEIGHT}")
        return img_byte_arr.getvalue()
        
    except Exception as e:
        logger.error(f"海报生成失败: {e}", exc_info=True)
        raise
