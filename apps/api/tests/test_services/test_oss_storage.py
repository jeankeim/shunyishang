"""
OSS 存储服务测试
覆盖: services/oss_storage.py
"""

import pytest
from io import BytesIO
from unittest.mock import patch, MagicMock
import sys


class TestOSSStorageService:
    """OSSStorageService 测试"""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_oss2 = MagicMock()
        self.mock_bucket = MagicMock()
        self.mock_oss2.Bucket.return_value = self.mock_bucket
        self.mock_oss2.Auth.return_value = MagicMock()

        self.settings_patch = patch("apps.api.services.oss_storage.settings")
        self.mock_settings = self.settings_patch.start()
        self.mock_settings.oss_access_key_id = "test-key"
        self.mock_settings.oss_access_key_secret = "test-secret"
        self.mock_settings.oss_bucket_name = "test-bucket"
        self.mock_settings.oss_endpoint = "https://oss-cn-hangzhou.aliyuncs.com"
        self.mock_settings.oss_public_url = "https://cdn.example.com"

        # Inject mock oss2 module
        self._orig_oss2 = sys.modules.get("oss2")
        sys.modules["oss2"] = self.mock_oss2
        yield
        self.settings_patch.stop()
        if self._orig_oss2 is not None:
            sys.modules["oss2"] = self._orig_oss2
        else:
            sys.modules.pop("oss2", None)

    def _create_service(self):
        from apps.api.services.oss_storage import OSSStorageService
        return OSSStorageService()

    def test_init_with_valid_config(self):
        svc = self._create_service()
        assert svc.bucket is not None

    def test_init_without_credentials(self):
        self.mock_settings.oss_access_key_id = None
        self.mock_settings.oss_access_key_secret = None
        svc = self._create_service()
        assert svc.bucket is None

    def test_init_import_error(self):
        sys.modules["oss2"] = None  # force ImportError
        svc = self._create_service()
        assert svc.bucket is None
        sys.modules["oss2"] = self.mock_oss2  # restore

    def test_init_oss2_exception(self):
        self.mock_oss2.Bucket.side_effect = Exception("init error")
        svc = self._create_service()
        assert svc.bucket is None
        self.mock_oss2.Bucket.side_effect = None

    def test_upload_file_no_bucket(self):
        self.mock_settings.oss_access_key_id = None
        self.mock_settings.oss_access_key_secret = None
        svc = self._create_service()
        url = svc.upload_file(BytesIO(b"data"), "test.jpg")
        assert url is None

    def test_upload_file_with_thumbnail(self):
        svc = self._create_service()
        from PIL import Image
        img = Image.new("RGB", (800, 600), color="red")
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        original_url, thumb_url = svc.upload_file_with_thumbnail(
            buf, "test.png", "uploads", "image/png"
        )
        assert original_url is not None
        assert thumb_url is not None
        assert "uploads/" in original_url
        assert "thumbnails/" in thumb_url
        assert self.mock_bucket.put_object.call_count == 2

    def test_upload_file_with_thumbnail_non_image(self):
        svc = self._create_service()
        buf = BytesIO(b"not an image")
        original_url, thumb_url = svc.upload_file_with_thumbnail(
            buf, "doc.pdf", "docs", "application/pdf"
        )
        assert original_url is not None
        assert thumb_url is None
        assert self.mock_bucket.put_object.call_count == 1

    def test_upload_file_error(self):
        self.mock_bucket.put_object.side_effect = Exception("upload error")
        svc = self._create_service()
        url, thumb = svc.upload_file_with_thumbnail(
            BytesIO(b"data"), "test.jpg", "uploads"
        )
        assert url is None
        assert thumb is None

    def test_upload_file_from_path(self, tmp_path):
        svc = self._create_service()
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")
        url = svc.upload_file_from_path(str(test_file))
        assert url is not None

    def test_upload_file_from_path_not_found(self):
        svc = self._create_service()
        url = svc.upload_file_from_path("/nonexistent/file.jpg")
        assert url is None

    def test_upload_file_from_path_no_bucket(self):
        self.mock_settings.oss_access_key_id = None
        self.mock_settings.oss_access_key_secret = None
        svc = self._create_service()
        url = svc.upload_file_from_path("/some/file.jpg")
        assert url is None

    def test_upload_file_from_path_exception(self, tmp_path):
        svc = self._create_service()
        self.mock_bucket.put_object.side_effect = Exception("error")
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"data")
        url = svc.upload_file_from_path(str(test_file))
        assert url is None

    def test_delete_file(self):
        svc = self._create_service()
        result = svc.delete_file("https://cdn.example.com/uploads/test.jpg")
        assert result is True
        self.mock_bucket.delete_object.assert_called_once()

    def test_delete_file_no_bucket(self):
        self.mock_settings.oss_access_key_id = None
        self.mock_settings.oss_access_key_secret = None
        svc = self._create_service()
        result = svc.delete_file("https://cdn.example.com/test.jpg")
        assert result is False

    def test_delete_file_error(self):
        self.mock_bucket.delete_object.side_effect = Exception("delete error")
        svc = self._create_service()
        result = svc.delete_file("https://cdn.example.com/test.jpg")
        assert result is False

    def test_file_exists(self):
        self.mock_bucket.object_exists.return_value = True
        svc = self._create_service()
        result = svc.file_exists("https://cdn.example.com/test.jpg")
        assert result is True

    def test_file_exists_no_bucket(self):
        self.mock_settings.oss_access_key_id = None
        self.mock_settings.oss_access_key_secret = None
        svc = self._create_service()
        result = svc.file_exists("https://cdn.example.com/test.jpg")
        assert result is False

    def test_file_exists_error(self):
        self.mock_bucket.object_exists.side_effect = Exception("error")
        svc = self._create_service()
        result = svc.file_exists("https://cdn.example.com/test.jpg")
        assert result is False

    def test_get_thumbnail_url(self):
        svc = self._create_service()
        url = svc.get_thumbnail_url("https://cdn.example.com/uploads/test.jpg")
        assert url is not None
        assert "thumbnails/" in url
        assert "_thumb" in url

    def test_get_thumbnail_url_empty(self):
        svc = self._create_service()
        assert svc.get_thumbnail_url("") is None
        assert svc.get_thumbnail_url(None) is None

    def test_get_thumbnail_url_error(self):
        svc = self._create_service()
        # Pass a URL that will cause _extract_key to fail in an unexpected way
        with patch.object(svc, '_extract_key', side_effect=Exception("error")):
            result = svc.get_thumbnail_url("https://cdn.example.com/test.jpg")
        assert result == "https://cdn.example.com/test.jpg"  # returns original on error

    def test_build_url_with_public_url(self):
        svc = self._create_service()
        url = svc._build_url("uploads/test.jpg")
        assert url == "https://cdn.example.com/uploads/test.jpg"

    def test_build_url_without_public_url(self):
        self.mock_settings.oss_public_url = ""
        svc = self._create_service()
        url = svc._build_url("uploads/test.jpg")
        assert "test-bucket" in url
        assert "uploads/test.jpg" in url

    def test_extract_key_with_public_url(self):
        svc = self._create_service()
        key = svc._extract_key("https://cdn.example.com/uploads/test.jpg")
        assert key == "uploads/test.jpg"

    def test_extract_key_without_public_url(self):
        self.mock_settings.oss_public_url = ""
        svc = self._create_service()
        key = svc._extract_key("https://test-bucket.oss.aliyuncs.com/uploads/test.jpg")
        assert key == "uploads/test.jpg"

    def test_extract_key_fallback(self):
        self.mock_settings.oss_public_url = ""
        svc = self._create_service()
        # URL that doesn't match standard patterns - tests the except branch
        key = svc._extract_key("not-a-url-file.jpg")
        assert "not-a-url-file.jpg" in key

    def test_generate_thumbnail_rgba(self):
        from PIL import Image
        svc = self._create_service()
        img = Image.new("RGBA", (800, 600), color=(255, 0, 0, 128))
        buf = BytesIO()
        img.save(buf, format="PNG")
        result = svc._generate_thumbnail(buf.getvalue())
        assert len(result) > 0

    def test_generate_thumbnail_p_mode(self):
        from PIL import Image
        svc = self._create_service()
        img = Image.new("P", (800, 600))
        buf = BytesIO()
        img.save(buf, format="PNG")
        result = svc._generate_thumbnail(buf.getvalue())
        assert len(result) > 0

    def test_generate_thumbnail_custom_width(self):
        from PIL import Image
        svc = self._create_service()
        img = Image.new("RGB", (800, 600), color="blue")
        buf = BytesIO()
        img.save(buf, format="PNG")
        result = svc._generate_thumbnail(buf.getvalue(), max_width=200)
        assert len(result) > 0

    def test_generate_thumbnail_error_returns_original(self):
        svc = self._create_service()
        result = svc._generate_thumbnail(b"invalid image data")
        assert result == b"invalid image data"

    def test_get_oss_service_singleton(self):
        import apps.api.services.oss_storage as mod
        mod._oss_service = None
        svc1 = mod.get_oss_service()
        svc2 = mod.get_oss_service()
        assert svc1 is svc2
        mod._oss_service = None
