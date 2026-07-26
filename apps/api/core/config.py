"""
FastAPI 应用配置模块
使用 pydantic-settings 从 .env 文件读取配置
"""

import secrets
import re
import logging
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # === 数据库配置 ===
    database_url: str = "postgresql://wuxing_user:wuxing_password@localhost:5432/wuxing_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # === 阿里百炼千问 LLM 配置 ===
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"  # 国际端点（境外服务器）
    qwen_model: str = "qwen-plus"  # 国内端点使用 qwen-plus（质量更高）
    qwen_vl_model: str = "qwen-vl-plus"  # 多模态视觉模型：拍照识别衣物五行属性
    
    # === OpenAI 配置 (备用) ===
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    
    # === Embedding 配置 ===
    embedding_model: str = "BGE-M3"
    embedding_dimension: int = 1024
    
    # === Redis 缓存配置 ===
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    cache_ttl_bazi: int = 86400
    cache_ttl_weather: int = 900
    cache_ttl_search: int = 3600
    
    # === Upstash Redis 配置 (生产环境) ===
    upstash_redis_rest_url: str = ""
    upstash_redis_rest_token: str = ""
    
    # === Cloudflare R2 对象存储配置 ===
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "wuxing-wardrobe"
    r2_public_url: str = ""
    
    # === 阿里云 OSS 对象存储配置（国内生产环境） ===
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_bucket_name: str = "shunyishang-images"
    oss_endpoint: str = "https://oss-cn-hangzhou-internal.aliyuncs.com"  # ECS 内网
    oss_public_url: str = ""  # 如 https://images.shunyishang.cn
    
    # === API 限流 / LLM 配额配置 ===
    rate_limit_enabled: bool = True                # 限流总开关（测试环境可关闭）
    rate_limit_global_per_minute: int = 120        # 全局：每 IP 每分钟最大请求数
    rate_limit_auth_per_minute: int = 5            # 登录/注册：每 IP 每分钟最大次数
    llm_quota_enabled: bool = True                 # LLM 日配额开关
    llm_daily_quota: int = 30                      # 每身份（登录用户/游客IP）每日 LLM 推荐次数

    # === PII 敏感字段加密（PIPL 合规）===
    # 生成密钥: python -m apps.api.core.pii_crypto genkey
    # 未配置时降级明文存储（仅限开发环境），生产环境必须配置
    pii_encryption_key: str = ""

    # === 错误监控（Sentry）===
    # 未配置 DSN 时不初始化，开发环境零影响
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1  # 性能追踪采样率（免费额度有限，保持低采样）

    # === JWT 配置 ===
    jwt_secret_key: str = ""  # 生产环境必须设置
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    
    # === 天气API配置 ===
    weather_api_key: str = ""  # 和风天气API Key
    amap_api_key: str = ""     # 高德地图API Key
    
    # === 应用配置 ===
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    
    # === CORS 配置 ===
    cors_origins: str = ""
    
    @property
    def cors_origins_list(self) -> List[str]:
        """解析 CORS origins 为列表（生产环境安全验证）"""
        if self.app_env == "production":
            # 生产环境：严格校验
            if not self.cors_origins or self.cors_origins == "*":
                raise ValueError(
                    "生产环境必须配置 CORS_ORIGINS，禁止使用通配符 '*'！"
                    "请设置具体域名，如: https://your-domain.com"
                )
            return [origin.strip() for origin in self.cors_origins.split(",")]
        else:
            # 开发环境：宽松模式
            if self.cors_origins == "*" or not self.cors_origins:
                return ["*"]
            return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.app_env == "development"
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.app_env == "production"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_jwt_secret()
        self._auto_enable_redis()
    
    def _auto_enable_redis(self):
        """自动启用 Redis（优先传统 Redis，兼容 Upstash）"""
        # 优先检测传统 Redis（阿里云 Redis，国内部署）
        if self.redis_url and self.redis_url != "redis://localhost:6379/0":
            if not self.redis_enabled:
                self.redis_enabled = True
                logger.info("[配置] ✅ 检测到 Redis 配置，自动启用缓存")
        # 兼容旧版 Upstash（过渡期保留）
        elif self.upstash_redis_rest_url and self.upstash_redis_rest_token:
            if not self.redis_enabled:
                self.redis_enabled = True
                logger.info("[配置] ✅ 检测到 Upstash Redis 配置，自动启用缓存")
    
    def _validate_jwt_secret(self):
        """JWT 密钥安全校验"""
        if not self.jwt_secret_key:
            # 开发环境自动生成
            if self.app_env == "development":
                logger.warning("⚠️  未设置 JWT_SECRET_KEY，开发环境自动生成临时密钥")
                self.jwt_secret_key = secrets.token_urlsafe(32)
            else:
                raise ValueError(
                    "生产环境必须设置 JWT_SECRET_KEY！"
                    "请生成强随机密钥并添加到 .env 文件中："
                    "JWT_SECRET_KEY=$(openssl rand -base64 32)"
                )
        else:
            # 检查密钥强度
            self._check_key_strength(self.jwt_secret_key)
    
    def _check_key_strength(self, key: str):
        """检查密钥强度"""
        # 开发环境警告
        if self.app_env == "development":
            if key == "your-super-secret-key" or len(key) < 32:
                logger.warning("⚠️  JWT_SECRET_KEY 强度较弱，建议使用更强的密钥")
            return
        
        # 生产环境强制校验
        if len(key) < 32:
            raise ValueError(
                f"JWT_SECRET_KEY 长度不足！生产环境需要至少 32 字符，当前: {len(key)}"
            )
        if not re.search(r'[A-Za-z]', key) or not re.search(r'[0-9]', key):
            raise ValueError(
                "JWT_SECRET_KEY 必须包含字母和数字的组合"
            )


# 全局配置实例
settings = Settings()
