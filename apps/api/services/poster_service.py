"""
海报生成服务 - 使用 Pillow 在服务端生成高质量海报
支持三种模板：简约风格、五行国潮、社交卡片
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

# 五行配色主题
WUXING_THEMES = {
    'fire': {
        'primary': '#FF6B6B',
        'secondary': '#FF8E53',
        'background': '#FAFAF8',
    },
    'wood': {
        'primary': '#4CAF50',
        'secondary': '#8BC34A',
        'background': '#F1F8E9',
    },
    'earth': {
        'primary': '#D4A574',
        'secondary': '#E6C9A8',
        'background': '#FFF8E1',
    },
    'metal': {
        'primary': '#9E9E9E',
        'secondary': '#BDBDBD',
        'background': '#F5F5F5',
    },
    'water': {
        'primary': '#2196F3',
        'secondary': '#64B5F6',
        'background': '#E3F2FD',
    },
}


def get_font(size: int, weight: str = 'normal') -> ImageFont.FreeTypeFont:
    """获取字体（优先使用系统中文字体）"""
    # 中文字体路径（macOS + Linux + Windows）
    font_paths = [
        # Linux (Docker) - Noto CJK
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
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


def download_image(url: str) -> Optional[Image.Image]:
    """下载图片并返回 PIL Image 对象"""
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
        
        # HTTP 下载
        logger.info(f"下载图片: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGBA')
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
    sign_font = get_font(36)
    draw.text((POSTER_WIDTH - 100, POSTER_HEIGHT - 60), f'—— {signature}', fill='#6B7280', font=sign_font, anchor='rm')
    
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
    
    # 底部品牌区
    footer_y = POSTER_HEIGHT - 120
    
    # 分隔线
    draw.line([(80, footer_y), (POSTER_WIDTH - 80, footer_y)], fill=(255, 255, 255, 25), width=2)
    
    # 左侧：品牌信息
    brand_x = 100
    brand_y = footer_y + 60
    
    # 品牌图标
    draw.rounded_rectangle(
        [brand_x, brand_y - 20, brand_x + 40, brand_y + 20],
        radius=8,
        fill=theme['primary'],
    )
    brand_icon_font = get_font(20, 'bold')
    draw.text((brand_x + 20, brand_y), '五行', fill='white', font=brand_icon_font, anchor='mm')
    
    # 品牌名称
    brand_font = get_font(28, 'bold')
    draw.text((brand_x + 60, brand_y - 10), '顺衣尚', fill='white', font=brand_font, anchor='lm')
    brand_sub_font = get_font(22)
    draw.text((brand_x + 60, brand_y + 20), '传统智慧 · 现代穿搭', fill=(255, 255, 255, 128), font=brand_sub_font, anchor='lm')
    
    # 右侧：生成时间和签名
    from datetime import datetime
    current_time = datetime.now().strftime('%H:%M:%S')
    
    time_font = get_font(24)
    draw.text((POSTER_WIDTH - 100, brand_y - 20), f'生成时间：{current_time}', fill=(255, 255, 255, 153), font=time_font, anchor='rm')
    
    sign_font = get_font(32, 'bold')
    draw.text((POSTER_WIDTH - 100, brand_y + 25), '—— 顺衣尚', fill=(255, 255, 255, 204), font=sign_font, anchor='rm')
    
    return img


def generate_card_poster(
    title: str,
    items: List[Dict],
    xiyong_elements: List[str],
    theme_name: str = 'fire',
    quote: str = '',
    signature: str = '顺衣尚',
    scene: str = '',
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
    
    # 用户头像圆圈
    avatar_x = header_x + 70
    avatar_y = header_y + header_height // 2
    draw.ellipse(
        [avatar_x - 35, avatar_y - 35, avatar_x + 35, avatar_y + 35],
        fill=theme['primary'],
    )
    avatar_font = get_font(36, 'bold')
    draw.text((avatar_x, avatar_y), 'U', fill='white', font=avatar_font, anchor='mm')
    
    # 用户名
    name_font = get_font(32, 'bold')
    draw.text((avatar_x + 70, avatar_y - 15), '@用户', fill='#212529', font=name_font, anchor='lm')
    
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
    grid_item_height = 280
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
        
        # 图片区域
        img_area_height = 200
        if item.get('image_url'):
            item_img = download_image(item['image_url'])
            if item_img:
                item_img = item_img.resize((grid_item_width, img_area_height), Image.Resampling.LANCZOS)
                img.paste(item_img, (item_x, item_y), item_img)
        
        # 序号标签
        num_bg_x = item_x + 16
        num_bg_y = item_y + 16
        draw.rounded_rectangle(
            [num_bg_x, num_bg_y, num_bg_x + 40, num_bg_y + 40],
            radius=20,
            fill=theme['primary'],
        )
        num_font = get_font(24, 'bold')
        draw.text((num_bg_x + 20, num_bg_y + 20), str(i + 1), fill='white', font=num_font, anchor='mm')
        
        # 物品名称
        name_y = item_y + img_area_height + 20
        name_font = get_font(28, 'bold')
        draw.text((item_x + 20, name_y), item['name'], fill='#212529', font=name_font, anchor='lm')
        
        # 五行标签
        if item.get('primary_element'):
            tag_x = item_x + 20
            tag_y = name_y + 45
            draw.rounded_rectangle(
                [tag_x, tag_y - 16, tag_x + 60, tag_y + 16],
                radius=16,
                fill=theme['primary'],
            )
            tag_font = get_font(22)
            draw.text((tag_x + 30, tag_y), item['primary_element'], fill='white', font=tag_font, anchor='mm')
    
    # 互动数据区域
    interaction_y = grid_start_y + 2 * (grid_item_height + grid_gap) + 40
    draw.rounded_rectangle(
        [80, interaction_y, POSTER_WIDTH - 80, interaction_y + 200],
        radius=24,
        fill=(255, 255, 255, 204),
        outline=(0, 0, 0, 15),
        width=2,
    )
    
    # 点赞等数据
    interaction_font = get_font(28)
    draw.text((120, interaction_y + 50), '❤️ 128', fill='#212529', font=interaction_font, anchor='lm')
    draw.text((260, interaction_y + 50), '💬 32', fill='#212529', font=interaction_font, anchor='lm')
    draw.text((400, interaction_y + 50), '↗️ 分享', fill='#212529', font=interaction_font, anchor='lm')
    
    # 标签
    tag_start_x = 120
    tag_y = interaction_y + 120
    for element in xiyong_elements:
        tag_width = 140
        draw.rounded_rectangle(
            [tag_start_x, tag_y - 20, tag_start_x + tag_width, tag_y + 20],
            radius=20,
            fill=theme['primary'],
        )
        tag_font = get_font(24, 'bold')
        draw.text((tag_start_x + tag_width // 2, tag_y), f'#{element}穿搭', fill='white', font=tag_font, anchor='mm')
        tag_start_x += tag_width + 16
    
    # 底部品牌标识
    footer_y = POSTER_HEIGHT - 80
    draw.line([(80, footer_y), (POSTER_WIDTH - 80, footer_y)], fill=(0, 0, 0, 15), width=2)
    
    brand_font = get_font(24, 'bold')
    draw.text((100, footer_y + 40), '顺衣尚', fill='#6B7280', font=brand_font, anchor='lm')
    
    date_font = get_font(24)
    from datetime import datetime
    draw.text((POSTER_WIDTH - 100, footer_y + 40), datetime.now().strftime('%Y-%m-%d'), fill='#9CA3AF', font=date_font, anchor='rm')
    
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
