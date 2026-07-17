"""
配置文件 - 数据工程模块全局配置
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ============================================================
# API Keys 配置（从环境变量读取）
# ============================================================

# 高德地图 Web服务 API Key
# 访问 https://lbs.amap.com/ 注册获取
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")

# 百度地图 API AK
# 访问 https://lbsyun.baidu.com/ 注册获取
BAIDU_MAP_AK = os.getenv("BAIDU_MAP_AK", "")

# Pixabay API Key
# 访问 https://pixabay.com/api/docs/ 注册获取
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
PIXABAY_API_URL = "https://pixabay.com/api/"
PIXABAY_RATE_LIMIT = 5000  # 免费API每小时5000次请求

# 请求间隔（秒），避免触发限流
REQUEST_INTERVAL = 0.5

# 请求重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2  # 重试间隔（秒）

# 分页配置
PAGE_SIZE = 25  # 每页条数（高德固定最多25）
MAX_PAGES = 1   # 每个城市每种POI类型最多爬取页数（1页≈25条，实际可用10-20条）

# ============================================================
# 目标城市配置
# ============================================================

# 是否爬取所有城市（默认True，覆盖全国所有城市）
# 每个城市每种POI类型只取1页（约10-20条），总请求量约 300城市×3类型=900次
USE_ALL_CITIES = True

# 重点城市列表（仅当 USE_ALL_CITIES=False 或通过 --cities 参数指定时生效）
TARGET_CITIES = [
    "北京", "上海", "广州", "深圳", "成都",
    "杭州", "南京", "武汉", "西安", "重庆",
]

# ============================================================
# POI 详情补全配置（评分/价格/开放时间）
# ============================================================

# 每个城市每种POI类型最多更新的POI数量（只更新前N条）
ENRICH_PER_CITY = 3

# 每个城市每种POI类型从百度地图搜索的最大页数
ENRICH_PAGES = 1

# 百度地图POI搜索关键词（query）映射
BAIDU_QUERY_MAP = {
    "scenic_spots": "景点",
    "hotels": "酒店",
    "restaurants": "餐饮",
}

# 百度地图POI搜索配置
BAIDU_PLACE_URL = "https://api.map.baidu.com/place/v2/search"
BAIDU_DETAIL_URL = "https://api.map.baidu.com/place/v2/detail"

# 要爬取的POI类型
# 键为高德API搜索关键词，值为对应的数据库表名
POI_TYPES = {
    "景点": "scenic_spots",
    "酒店": "hotels",
    "餐饮服务": "restaurants",
}

# ============================================================
# 数据库配置
# ============================================================

# 数据库类型: "sqlite"（开发测试）或 "mysql"（生产环境）
DB_TYPE = os.getenv("XINGZHI_DB_TYPE", "sqlite")

# SQLite 配置
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "xingzhi.db")

# MySQL 配置（当 DB_TYPE = "mysql" 时使用）
DB_HOST = os.getenv("XINGZHI_DB_HOST", "localhost")
DB_PORT = int(os.getenv("XINGZHI_DB_PORT", "3306"))
DB_USER = os.getenv("XINGZHI_DB_USER", "root")
DB_PASSWORD = os.getenv("XINGZHI_DB_PASSWORD", "")
DB_NAME = os.getenv("XINGZHI_DB_NAME", "xingzhi")

# ============================================================
# 数据文件路径
# ============================================================

# 原始数据保存目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# CSV 文件路径
CITIES_CSV = os.path.join(DATA_DIR, "cities.csv")
SCENIC_SPOTS_CSV = os.path.join(DATA_DIR, "scenic_spots.csv")
HOTELS_CSV = os.path.join(DATA_DIR, "hotels.csv")
RESTAURANTS_CSV = os.path.join(DATA_DIR, "restaurants.csv")