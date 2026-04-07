"""
FastAPI 应用配置模块
使用 pydantic-settings 从 .env 文件读取配置
"""

import secrets
import re
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    qwen_model: str = "qwen-plus"
    
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
    
    def _validate_jwt_secret(self):
        """JWT 密钥安全校验"""
        if not self.jwt_secret_key:
            # 开发环境自动生成
            if self.app_env == "development":
                print("⚠️  未设置 JWT_SECRET_KEY，开发环境自动生成临时密钥")
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
                print("⚠️  JWT_SECRET_KEY 强度较弱，建议使用更强的密钥")
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
