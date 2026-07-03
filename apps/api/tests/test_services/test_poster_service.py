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
