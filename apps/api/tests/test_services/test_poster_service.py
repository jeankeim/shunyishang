"""
海报生成服务测试
覆盖 poster_service.py 所有方法
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from PIL import Image

from apps.api.services.poster_service import (
    get_font,
    download_image,
    create_gradient_background,
    generate_simple_poster,
    generate_wuxing_poster,
    generate_card_poster,
    generate_poster,
    WUXING_THEMES,
    POSTER_WIDTH,
    POSTER_HEIGHT,
)
from apps.api.services.poster_service import (
    generate_guofeng_poster,
    get_serif_font,
    hex_to_rgb,
    wrap_text,
    pick_main_item_index,
    get_lunar_date_str,
    GUOFENG_THEMES,
)


class TestGetFont:
    def test_returns_font(self):
        """应返回一个字体对象"""
        font = get_font(36)
        assert font is not None

    def test_bold_weight(self):
        font = get_font(36, 'bold')
        assert font is not None

    def test_normal_weight(self):
        font = get_font(28, 'normal')
        assert font is not None


class TestDownloadImage:
    def test_http_success(self):
        """HTTP 下载成功"""
        img = Image.new('RGB', (100, 100), color='red')
        buf = BytesIO()
        img.save(buf, format='PNG')
        mock_resp = MagicMock()
        mock_resp.content = buf.getvalue()
        mock_resp.raise_for_status = MagicMock()
        with patch("apps.api.services.poster_service.requests.get", return_value=mock_resp):
            result = download_image("http://example.com/test.png")
        assert result is not None
        assert result.mode == 'RGBA'

    def test_http_error(self):
        """HTTP 下载失败返回 None"""
        with patch("apps.api.services.poster_service.requests.get", side_effect=Exception("network error")):
            result = download_image("http://example.com/test.png")
        assert result is None

    def test_seed_image_not_found(self):
        """seed 图片不存在"""
        result = download_image("/images/seed/nonexistent.png")
        assert result is None

    def test_uploads_image_not_found(self):
        """uploads 图片不存在"""
        result = download_image("/uploads/wardrobe/nonexistent.png")
        assert result is None

    def test_relative_path_other(self):
        """其他相对路径"""
        with patch("apps.api.services.poster_service.requests.get", side_effect=Exception("fail")):
            with patch.dict("os.environ", {"BACKEND_URL": "http://localhost:8000"}):
                result = download_image("/other/path.png")
        assert result is None


class TestCreateGradientBackground:
    def test_basic(self):
        img = create_gradient_background(100, 200, '#FF0000', '#0000FF')
        assert img.size == (100, 200)
        assert img.mode == 'RGB'

    def test_same_color(self):
        img = create_gradient_background(50, 50, '#00FF00', '#00FF00')
        assert img.size == (50, 50)


class TestGenerateSimplePoster:
    def test_basic(self):
        """基本简约海报生成"""
        items = [
            {"name": "红色T恤", "primary_element": "火", "image_url": ""},
            {"name": "蓝色牛仔裤", "primary_element": "水", "image_url": ""},
        ]
        img = generate_simple_poster(
            title="今日穿搭",
            items=items,
            xiyong_elements=["火", "木"],
            theme_name='fire',
            quote="测试引言",
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_no_quote(self):
        """无引言"""
        items = [{"name": "白衬衫", "primary_element": "金", "image_url": ""}]
        img = generate_simple_poster(
            title="简约穿搭",
            items=items,
            xiyong_elements=["金"],
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_with_image_url(self):
        """带图片 URL"""
        mock_img = Image.new('RGBA', (200, 200), color=(255, 0, 0, 255))
        items = [{"name": "红衣", "primary_element": "火", "image_url": "http://example.com/img.png"}]
        with patch("apps.api.services.poster_service.download_image", return_value=mock_img):
            img = generate_simple_poster(
                title="测试",
                items=items,
                xiyong_elements=[],
            )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_image_download_fail(self):
        """图片下载失败"""
        items = [{"name": "红衣", "primary_element": "火", "image_url": "http://example.com/notfound.png"}]
        with patch("apps.api.services.poster_service.download_image", return_value=None):
            img = generate_simple_poster(
                title="测试",
                items=items,
                xiyong_elements=[],
            )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_different_themes(self):
        """不同五行主题"""
        for theme in ['fire', 'wood', 'earth', 'metal', 'water']:
            items = [{"name": "测试", "primary_element": "金", "image_url": ""}]
            img = generate_simple_poster(
                title=f"主题{theme}",
                items=items,
                xiyong_elements=[],
                theme_name=theme,
            )
            assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_unknown_theme(self):
        """未知主题使用默认 fire"""
        items = [{"name": "测试", "primary_element": "金", "image_url": ""}]
        img = generate_simple_poster(
            title="测试",
            items=items,
            xiyong_elements=[],
            theme_name='unknown',
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_many_items(self):
        """超过5个物品截断"""
        items = [{"name": f"物品{i}", "primary_element": "金", "image_url": ""} for i in range(10)]
        img = generate_simple_poster(
            title="多物品",
            items=items,
            xiyong_elements=["金"],
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_no_items(self):
        """无物品"""
        img = generate_simple_poster(
            title="空穿搭",
            items=[],
            xiyong_elements=[],
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_with_scene(self):
        """带场景参数"""
        items = [{"name": "西装", "primary_element": "金", "image_url": ""}]
        img = generate_simple_poster(
            title="商务穿搭",
            items=items,
            xiyong_elements=["金"],
            scene="商务",
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)


class TestGenerateWuxingPoster:
    def test_basic(self):
        """基本五行国潮海报"""
        items = [
            {"name": "红色连衣裙", "primary_element": "火", "color": "红色", "image_url": ""},
            {"name": "金色项链", "primary_element": "金", "color": "金色", "image_url": ""},
        ]
        img = generate_wuxing_poster(
            title="五行穿搭",
            items=items,
            xiyong_elements=["火"],
            theme_name='fire',
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_no_xiyong(self):
        """无喜用神"""
        items = [{"name": "白衬衫", "primary_element": "金", "image_url": ""}]
        img = generate_wuxing_poster(
            title="测试",
            items=items,
            xiyong_elements=[],
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_with_image(self):
        """带图片"""
        mock_img = Image.new('RGBA', (200, 200), color=(0, 255, 0, 255))
        items = [{"name": "绿衣", "primary_element": "木", "color": "绿色", "image_url": "http://example.com/green.png"}]
        with patch("apps.api.services.poster_service.download_image", return_value=mock_img):
            img = generate_wuxing_poster(
                title="木属性穿搭",
                items=items,
                xiyong_elements=["木"],
                theme_name='wood',
            )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_no_color_field(self):
        """无颜色字段"""
        items = [{"name": "黑裤", "primary_element": "水", "image_url": ""}]
        img = generate_wuxing_poster(
            title="测试",
            items=items,
            xiyong_elements=["水"],
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)


class TestGenerateCardPoster:
    def test_basic(self):
        """基本社交卡片海报"""
        items = [
            {"name": "上衣", "primary_element": "火", "image_url": ""},
            {"name": "裤子", "primary_element": "水", "image_url": ""},
            {"name": "鞋子", "primary_element": "木", "image_url": ""},
            {"name": "帽子", "primary_element": "金", "image_url": ""},
        ]
        img = generate_card_poster(
            title="今日穿搭分享",
            items=items,
            xiyong_elements=["火", "金"],
            theme_name='fire',
            scene="约会",
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_no_scene(self):
        """无场景"""
        items = [{"name": "白T", "primary_element": "金", "image_url": ""}]
        img = generate_card_poster(
            title="日常穿搭",
            items=items,
            xiyong_elements=[],
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_with_image(self):
        """带图片"""
        mock_img = Image.new('RGBA', (440, 200), color=(0, 0, 255, 255))
        items = [{"name": "蓝衣", "primary_element": "水", "image_url": "http://example.com/blue.png"}]
        with patch("apps.api.services.poster_service.download_image", return_value=mock_img):
            img = generate_card_poster(
                title="测试",
                items=items,
                xiyong_elements=["水"],
            )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_more_than_four_items(self):
        """超过4个物品截断"""
        items = [{"name": f"物品{i}", "primary_element": "金", "image_url": ""} for i in range(8)]
        img = generate_card_poster(
            title="多物品",
            items=items,
            xiyong_elements=["金"],
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)


class TestGeneratePoster:
    def test_simple_layout(self):
        """简约布局"""
        items = [{"name": "测试", "primary_element": "金", "image_url": ""}]
        result = generate_poster(
            layout='simple',
            title="测试",
            items=items,
            xiyong_elements=["金"],
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_wuxing_layout(self):
        """五行布局"""
        items = [{"name": "测试", "primary_element": "火", "image_url": ""}]
        result = generate_poster(
            layout='wuxing',
            title="测试",
            items=items,
            xiyong_elements=["火"],
        )
        assert isinstance(result, bytes)

    def test_card_layout(self):
        """卡片布局"""
        items = [{"name": "测试", "primary_element": "木", "image_url": ""}]
        result = generate_poster(
            layout='card',
            title="测试",
            items=items,
            xiyong_elements=["木"],
        )
        assert isinstance(result, bytes)

    def test_unknown_layout(self):
        """未知布局使用 simple"""
        items = [{"name": "测试", "primary_element": "金", "image_url": ""}]
        result = generate_poster(
            layout='unknown',
            title="测试",
            items=items,
            xiyong_elements=[],
        )
        assert isinstance(result, bytes)

    def test_no_items(self):
        """无物品"""
        result = generate_poster(
            layout='simple',
            title="空海报",
            items=None,
            xiyong_elements=None,
        )
        assert isinstance(result, bytes)

    def test_error_raises(self):
        """异常时抛出"""
        with patch("apps.api.services.poster_service.generate_simple_poster", side_effect=Exception("fail")):
            with pytest.raises(Exception):
                generate_poster(layout='simple', title="test")

    def test_all_themes(self):
        """所有五行主题"""
        items = [{"name": "测试", "primary_element": "金", "image_url": ""}]
        for theme in ['fire', 'wood', 'earth', 'metal', 'water']:
            result = generate_poster(
                layout='simple',
                title=f"主题{theme}",
                items=items,
                xiyong_elements=[theme],
                theme=theme,
            )
            assert isinstance(result, bytes)

    def test_with_quote_and_signature(self):
        """带引言和签名"""
        items = [{"name": "测试", "primary_element": "金", "image_url": ""}]
        result = generate_poster(
            layout='simple',
            title="测试",
            items=items,
            xiyong_elements=["金"],
            quote="每日一句",
            signature="测试用户",
            scene="商务",
        )
        assert isinstance(result, bytes)


# ============================================================
# 宋锦国风模板测试
# ============================================================

class TestGuofengHelpers:
    """国风模板辅助函数"""

    def test_get_serif_font(self):
        font = get_serif_font(32)
        assert font is not None

    def test_hex_to_rgb(self):
        assert hex_to_rgb('#4E8560') == (78, 133, 96)
        assert hex_to_rgb('#FFFFFF') == (255, 255, 255)

    def test_wrap_text_short(self):
        """短文本不折行"""
        img = Image.new('RGB', (100, 50))
        draw = Image.new('RGB', (1, 1))  # 仅用于占位
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        lines = wrap_text(draw, '短文本', get_serif_font(20), 500)
        assert lines == ['短文本']

    def test_wrap_text_long(self):
        """长文本折多行"""
        from PIL import ImageDraw
        img = Image.new('RGB', (100, 50))
        draw = ImageDraw.Draw(img)
        lines = wrap_text(draw, '甲乙丙丁戊己庚辛壬癸', get_serif_font(20), 60)
        assert len(lines) > 1
        assert ''.join(lines) == '甲乙丙丁戊己庚辛壬癸'

    def test_pick_main_item_priority(self):
        """主件按品类优先级选择：外套 > 上装"""
        items = [
            {'name': '戒指', 'category': '配饰'},
            {'name': '衬衫', 'category': '上装'},
            {'name': '防晒衣', 'category': '外套'},
        ]
        assert pick_main_item_index(items) == 2

    def test_pick_main_item_no_priority_category(self):
        """无优先品类时取首件"""
        items = [
            {'name': '戒指', 'category': '配饰'},
            {'name': '帆布鞋', 'category': '鞋履'},
        ]
        assert pick_main_item_index(items) == 0

    def test_pick_main_item_empty_category(self):
        """category 缺失不报错"""
        items = [{'name': '无品类'}, {'name': '上装', 'category': '上装'}]
        assert pick_main_item_index(items) == 1

    def test_lunar_date_str(self):
        """农历返回干支纪年格式或空串"""
        result = get_lunar_date_str()
        assert isinstance(result, str)
        if result:  # cnlunar 可用时验证格式
            assert '年' in result
            assert '大' not in result and '小' not in result


class TestGuofengPoster:
    """宋锦国风海报生成"""

    def _sample_items(self, n=5):
        categories = ['上装', '鞋履', '外套', '配饰', '下装', '连衣裙']
        elements = ['木', '水', '火', '土', '金', '水']
        return [
            {
                'name': f'测试物品{i + 1}',
                'primary_element': elements[i % len(elements)],
                'category': categories[i % len(categories)],
                'color': '青色',
                'reason': f'推荐理由{i + 1}，五行相生，运势亨通',
            }
            for i in range(n)
        ]

    def test_basic_generates_png(self):
        img = generate_guofeng_poster(
            title='今日五行穿搭推荐',
            items=self._sample_items(),
            xiyong_elements=['木', '水'],
            theme_name='wood',
            quote='木气生发，水养其根。',
            username='测试用户',
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_dispatch_via_generate_poster(self):
        """layout='guofeng' 正确分发"""
        result = generate_poster(
            layout='guofeng',
            title='国风测试',
            items=self._sample_items(),
            xiyong_elements=['火'],
            theme='fire',
            quote='火助运势',
            username='用户',
        )
        assert isinstance(result, bytes)
        # 验证为合法 PNG
        parsed = Image.open(BytesIO(result))
        assert parsed.format == 'PNG'

    def test_all_themes(self):
        """五种国风主题均可生成"""
        for theme in GUOFENG_THEMES:
            img = generate_guofeng_poster(
                title='主题测试',
                items=self._sample_items(3),
                xiyong_elements=['木'],
                theme_name=theme,
            )
            assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_unknown_theme_fallback(self):
        img = generate_guofeng_poster(
            title='未知主题',
            items=self._sample_items(2),
            xiyong_elements=[],
            theme_name='unknown_theme',
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_no_items(self):
        """无物品也能生成（仅标题+五行环带+页脚）"""
        img = generate_guofeng_poster(
            title='空衣单',
            items=[],
            xiyong_elements=[],
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_many_items_capped_at_six(self):
        """超过 6 件只展示前 6 件不报错"""
        img = generate_guofeng_poster(
            title='多物品',
            items=self._sample_items(10),
            xiyong_elements=['金'],
            theme_name='metal',
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_single_item(self):
        """单件物品（仅主件无清单）"""
        img = generate_guofeng_poster(
            title='单品',
            items=self._sample_items(1),
            xiyong_elements=['水'],
            theme_name='water',
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_quote_hidden_for_many_items(self):
        """物品 >=5 件时引言不展示（保完整搭配），仍正常生成"""
        img = generate_guofeng_poster(
            title='多物品带引言',
            items=self._sample_items(5),
            xiyong_elements=['木'],
            quote='这段引言不应渲染',
        )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_with_image_download_mocked(self):
        """图片下载成功时合成到海报"""
        fake_img = Image.new('RGBA', (200, 200), (255, 0, 0, 255))
        with patch('apps.api.services.poster_service.download_image', return_value=fake_img):
            img = generate_guofeng_poster(
                title='带图',
                items=[{'name': '红衣', 'image_url': 'http://x.com/a.png',
                        'primary_element': '火', 'category': '上装', 'reason': '火旺'}],
                xiyong_elements=['火'],
                theme_name='fire',
            )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_image_download_fail_graceful(self):
        """图片下载失败不阻断生成"""
        with patch('apps.api.services.poster_service.download_image', return_value=None):
            img = generate_guofeng_poster(
                title='图失败',
                items=[{'name': '衣物', 'image_url': 'http://x.com/404.png',
                        'primary_element': '木', 'category': '配饰'}],
                xiyong_elements=['木'],
            )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)

    def test_lunar_failure_graceful(self):
        """农历解析失败不影响生成"""
        with patch('apps.api.services.poster_service.get_lunar_date_str', return_value=''):
            img = generate_guofeng_poster(
                title='无农历',
                items=self._sample_items(2),
                xiyong_elements=['土'],
                theme_name='earth',
            )
        assert img.size == (POSTER_WIDTH, POSTER_HEIGHT)
