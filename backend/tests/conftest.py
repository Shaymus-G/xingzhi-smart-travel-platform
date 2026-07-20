"""Backend 测试公共配置 — 提供测试环境变量，避免依赖真实 .env 文件"""
import os
import sys


def pytest_configure():
    """pytest 启动时设置测试所需环境变量。

    在导入任何 backend 模块之前设置，避免 Settings() 实例化失败。
    """
    # 数据库（测试用假值，不连接真实数据库）
    os.environ.setdefault("MYSQL_HOST", "localhost")
    os.environ.setdefault("MYSQL_PORT", "3306")
    os.environ.setdefault("MYSQL_USER", "test")
    os.environ.setdefault("MYSQL_PASSWORD", "test")
    os.environ.setdefault("MYSQL_DATABASE", "test")
    # JWT
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
    # DeepSeek（留空，AI 测试通过 Mock）
    os.environ.setdefault("DEEPSEEK_API_KEY", "")
    os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-chat")
    os.environ.setdefault("DEEPSEEK_TIMEOUT_SECONDS", "30")
