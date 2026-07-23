from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 基于 config.py 文件位置计算 backend/.env 的稳定路径，
# 避免 env_file=".env" 依赖当前工作目录。
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_env_path),
        encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "XingZhi Backend"
    DEBUG: bool = True

    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str

    SECRET_KEY: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 小时

    # CORS — 逗号分隔的允许来源，为空时开发模式全开
    CORS_ORIGINS: str = ""

    OPENWEATHER_KEY: str = ""

    # 高德地图 API
    AMAP_KEY: str = ""

    # DeepSeek AI 配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    DEEPSEEK_TIMEOUT_SECONDS: float = 30.0


settings = Settings()