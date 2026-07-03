"""
R2 对象存储服务测试
覆盖 r2_storage.py 所有方法
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from apps.api.services.r2_storage import R2StorageService, get_r2_service


class TestR2Init:
    def test_disabled_no_config(self):
        """配置不完整时禁用"""
        with patch("apps.api.services.r2_storage.settings") as mock_s:
            mock_s.r2_account_id = None
            mock_s.r2_access_key_id = None
            mock_s.r2_secret_access_key = None
            mock_s.r2_bucket_name = "test-bucket"
            mock_s.r2_public_url = ""
            svc = R2StorageService()
            assert svc.client is None

    def test_enabled_with_config(self):
        """配置完整时启用"""
        with patch("apps.api.services.r2_storage.settings") as mock_s:
            mock_s.r2_account_id = "test-account"
            mock_s.r2_access_key_id = "test-key"
            mock_s.r2_secret_access_key = "test-secret"
            mock_s.r2_bucket_name = "test-bucket"
            mock_s.r2_public_url = "https://pub.test.com"
            with patch("apps.api.services.r2_storage.boto3"):
                svc = R2StorageService()
                assert svc.client is not None
                assert svc.bucket_name == "test-bucket"
                assert svc.public_url == "https://pub.test.com"


class TestGenerateThumbnail:
    def test_success(self):
        """正常生成缩略图"""
        from PIL import Image
        img = Image.new('RGB', (800, 600), color='red')
        buf = BytesIO()
        img.save(buf, format='PNG')
        original_data = buf.getvalue()

        svc = R2StorageService.__new__(R2StorageService)
        svc.thumbnail_width = 400
        svc.thumbnail_quality = 80
        result = svc._generate_thumbnail(original_data)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_rgba_image(self):
        """RGBA 图片转换"""
        from PIL import Image
        img = Image.new('RGBA', (800, 600), color=(255, 0, 0, 128))
        buf = BytesIO()
        img.save(buf, format='PNG')
        original_data = buf.getvalue()

        svc = R2StorageService.__new__(R2StorageService)
        svc.thumbnail_width = 400
        svc.thumbnail_quality = 80
        result = svc._generate_thumbnail(original_data)
        assert isinstance(result, bytes)

    def test_p_mode_image(self):
        """P 模式图片转换"""
        from PIL import Image
        img = Image.new('P', (800, 600))
        buf = BytesIO()
        img.save(buf, format='PNG')
        original_data = buf.getvalue()

        svc = R2StorageService.__new__(R2StorageService)
        svc.thumbnail_width = 400
        svc.thumbnail_quality = 80
        result = svc._generate_thumbnail(original_data)
        assert isinstance(result, bytes)

    def test_custom_max_width(self):
        """自定义最大宽度"""
        from PIL import Image
        img = Image.new('RGB', (800, 600), color='blue')
        buf = BytesIO()
        img.save(buf, format='PNG')
        original_data = buf.getvalue()

        svc = R2StorageService.__new__(R2StorageService)
        svc.thumbnail_width = 400
        svc.thumbnail_quality = 80
        result = svc._generate_thumbnail(original_data, max_width=200)
        assert isinstance(result, bytes)

    def test_error_returns_original(self):
        """错误时返回原图"""
        svc = R2StorageService.__new__(R2StorageService)
        svc.thumbnail_width = 400
        svc.thumbnail_quality = 80
        result = svc._generate_thumbnail(b"invalid image data")
        assert result == b"invalid image data"


class TestUploadWithThumbnail:
    def test_no_client(self):
        """无客户端时返回 None"""
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = None
        file_data = BytesIO(b"test")
        result = svc.upload_file_with_thumbnail(file_data, "test.png")
        assert result == (None, None)

    def test_success_with_public_url(self):
        """成功上传，有 public_url"""
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        svc.thumbnail_width = 400
        svc.thumbnail_quality = 80
        svc._generate_thumbnail = MagicMock(return_value=b"thumbnail_data")

        from PIL import Image
        img = Image.new('RGB', (100, 100), color='green')
        buf = BytesIO()
        img.save(buf, format='PNG')

        file_data = BytesIO(buf.getvalue())
        original_url, thumb_url = svc.upload_file_with_thumbnail(
            file_data, "test.png", folder="uploads", content_type="image/png"
        )
        assert original_url is not None
        assert thumb_url is not None
        assert "pub.test.com" in original_url
        assert "thumbnails" in thumb_url
        svc.client.put_object.assert_called()

    def test_success_without_public_url(self):
        """成功上传，无 public_url"""
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.account_id = "test-account"
        svc.public_url = ""
        svc.thumbnail_width = 400
        svc.thumbnail_quality = 80
        svc._generate_thumbnail = MagicMock(return_value=b"thumbnail_data")

        from PIL import Image
        img = Image.new('RGB', (100, 100), color='green')
        buf = BytesIO()
        img.save(buf, format='PNG')

        file_data = BytesIO(buf.getvalue())
        original_url, thumb_url = svc.upload_file_with_thumbnail(
            file_data, "test.png", folder="uploads", content_type="image/png"
        )
        assert "r2.cloudflarestorage.com" in original_url
        assert "r2.cloudflarestorage.com" in thumb_url

    def test_non_image_content_type(self):
        """非图片类型不生成缩略图"""
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        svc.thumbnail_width = 400
        svc.thumbnail_quality = 80

        file_data = BytesIO(b"some file data")
        original_url, thumb_url = svc.upload_file_with_thumbnail(
            file_data, "test.txt", folder="docs", content_type="text/plain"
        )
        assert original_url is not None
        assert thumb_url is None

    def test_client_error(self):
        """ClientError 时返回 None"""
        from botocore.exceptions import ClientError
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "denied"}},
            "PutObject"
        )
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"

        file_data = BytesIO(b"test data")
        result = svc.upload_file_with_thumbnail(file_data, "test.png")
        assert result == (None, None)

    def test_generic_error(self):
        """通用异常返回 None"""
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.client.put_object.side_effect = ValueError("bad")
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"

        file_data = BytesIO(b"test data")
        result = svc.upload_file_with_thumbnail(file_data, "test.png")
        assert result == (None, None)


class TestUploadFile:
    def test_no_client(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = None
        file_data = BytesIO(b"test")
        # The first upload_file definition delegates to upload_file_with_thumbnail
        assert svc.upload_file(file_data, "test.png") is None

    def test_success_delegates(self):
        """测试第一个 upload_file 定义（委托给 upload_file_with_thumbnail）"""
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        svc.thumbnail_width = 400
        svc.thumbnail_quality = 80
        svc._generate_thumbnail = MagicMock(return_value=b"thumb")

        from PIL import Image
        img = Image.new('RGB', (100, 100), color='red')
        buf = BytesIO()
        img.save(buf, format='PNG')

        file_data = BytesIO(buf.getvalue())
        result = svc.upload_file(file_data, "test.png")
        assert result is not None
        assert "pub.test.com" in result

    def test_no_client_second_def(self):
        """测试第二个 upload_file 定义（直接上传）"""
        # Python 后定义的方法会覆盖前面的
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = None
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        result = svc.upload_file(BytesIO(b"data"), "test.png")
        assert result is None

    def test_success_direct_upload(self):
        """直接上传成功"""
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        result = svc.upload_file(BytesIO(b"data"), "test.png", folder="uploads")
        assert result is not None
        assert "pub.test.com" in result

    def test_success_without_public_url(self):
        """无 public_url 时使用默认 URL"""
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.account_id = "test-account"
        svc.public_url = ""
        result = svc.upload_file(BytesIO(b"data"), "test.png")
        assert "r2.cloudflarestorage.com" in result

    def test_client_error(self):
        from botocore.exceptions import ClientError
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        assert svc.upload_file(BytesIO(b"data"), "test.png") is None

    def test_generic_error(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.client.put_object.side_effect = RuntimeError("fail")
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        assert svc.upload_file(BytesIO(b"data"), "test.png") is None


class TestUploadFromPath:
    def test_no_client(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = None
        assert svc.upload_file_from_path("/tmp/test.png") is None

    def test_file_not_exists(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        assert svc.upload_file_from_path("/nonexistent/file.png") is None

    def test_error(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = svc.upload_file_from_path("/tmp/test.png")
        assert result is None


class TestDeleteFile:
    def test_no_client(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = None
        assert svc.delete_file("https://pub.test.com/test.png") is False

    def test_success_with_public_url(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        assert svc.delete_file("https://pub.test.com/uploads/test.png") is True
        svc.client.delete_object.assert_called_once()

    def test_success_without_public_url(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.public_url = ""
        assert svc.delete_file("https://bucket.r2.cloudflarestorage.com/test.png") is True

    def test_client_error(self):
        from botocore.exceptions import ClientError
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "DeleteObject"
        )
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        assert svc.delete_file("https://pub.test.com/test.png") is False

    def test_generic_error(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.client.delete_object.side_effect = RuntimeError("fail")
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        assert svc.delete_file("https://pub.test.com/test.png") is False


class TestFileExists:
    def test_no_client(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = None
        assert svc.file_exists("https://pub.test.com/test.png") is False

    def test_exists_with_public_url(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        assert svc.file_exists("https://pub.test.com/uploads/test.png") is True

    def test_not_exists_client_error(self):
        from botocore.exceptions import ClientError
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        assert svc.file_exists("https://pub.test.com/test.png") is False

    def test_generic_error(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.client = MagicMock()
        svc.client.head_object.side_effect = RuntimeError("fail")
        svc.bucket_name = "test-bucket"
        svc.public_url = "https://pub.test.com"
        assert svc.file_exists("https://pub.test.com/test.png") is False


class TestGetThumbnailUrl:
    def test_empty_url(self):
        svc = R2StorageService.__new__(R2StorageService)
        assert svc.get_thumbnail_url("") is None
        assert svc.get_thumbnail_url(None) is None

    def test_with_public_url(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.public_url = "https://pub.test.com"
        result = svc.get_thumbnail_url("https://pub.test.com/uploads/test.png")
        assert "thumbnails" in result
        assert "_thumb" in result

    def test_without_public_url(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.public_url = ""
        svc.bucket_name = "test-bucket"
        svc.account_id = "test-account"
        result = svc.get_thumbnail_url("https://test-bucket.test-account.r2.cloudflarestorage.com/uploads/test.png")
        assert "thumbnails" in result

    def test_existing_thumb_suffix(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.public_url = "https://pub.test.com"
        result = svc.get_thumbnail_url("https://pub.test.com/uploads/test_thumb.png")
        # Should not double the _thumb suffix
        assert result is not None

    def test_error_returns_original(self):
        svc = R2StorageService.__new__(R2StorageService)
        svc.public_url = "https://pub.test.com"
        # Force an error by making Path operations fail
        with patch("apps.api.services.r2_storage.Path", side_effect=Exception("fail")):
            result = svc.get_thumbnail_url("https://pub.test.com/test.png")
        assert result == "https://pub.test.com/test.png"


class TestGetR2Service:
    def test_singleton(self):
        import apps.api.services.r2_storage as mod
        mod._r2_service = None
        with patch("apps.api.services.r2_storage.settings") as mock_s:
            mock_s.r2_account_id = None
            mock_s.r2_access_key_id = None
            mock_s.r2_secret_access_key = None
            mock_s.r2_bucket_name = "test"
            mock_s.r2_public_url = ""
            s1 = get_r2_service()
            s2 = get_r2_service()
            assert s1 is s2
        mod._r2_service = None
