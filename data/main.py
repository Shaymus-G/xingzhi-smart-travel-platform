"""
主入口程序

编排整个数据工程流程：城市爬取 → POI爬取 → 数据清洗 → 数据入库
支持命令行参数，可灵活选择执行步骤。
"""

import argparse
import csv
import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from amap_client import AMapClient
from city_crawler import CityCrawler
from poi_crawler import PoiCrawler
from data_cleaner import DataCleaner
from db_manager import DatabaseManager
from poi_detail_updater import PoiDetailUpdater
from models import ScenicSpot, Hotel, Restaurant
from config import (
    USE_ALL_CITIES, POI_TYPES, DATA_DIR,
    CITIES_CSV, SCENIC_SPOTS_CSV, HOTELS_CSV, RESTAURANTS_CSV,
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME,
)

# ============================================================
# 日志配置
# ============================================================

def setup_logging():
    """配置日志输出"""
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


# ============================================================
# 数据保存
# ============================================================

def save_to_csv(data: list, filepath: str, fieldnames: list = None):
    """
    将数据保存为CSV文件

    Args:
        data: 字典列表
        filepath: 保存路径
        fieldnames: 字段名列表，默认使用第一个字典的键
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    if not data:
        logging.warning(f"没有数据可保存到 {filepath}")
        return

    if not fieldnames:
        fieldnames = list(data[0].keys())

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    logging.info(f"数据已保存至: {filepath} ({len(data)} 条)")


# ============================================================
# 各步骤实现
# ============================================================

def step_init_db(args):
    """步骤0：初始化数据库（创建表）"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("步骤0: 初始化数据库")
    logger.info("=" * 50)

    db = DatabaseManager()
    db.connect()
    db.create_tables()

    logger.info("数据库初始化完成！")


def step_cities(args):
    """步骤1：爬取城市数据"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("步骤1: 爬取城市数据")
    logger.info("=" * 50)

    crawler = CityCrawler()
    cities = crawler.get_target_cities(args.cities if args.cities else None)

    if not cities:
        logger.error("未获取到城市数据，请检查API Key和网络连接")
        return []

    # 清洗城市数据
    cleaner = DataCleaner()
    cleaned_cities = [cleaner.clean_city(c) for c in cities]

    # 保存到CSV
    save_to_csv(cleaned_cities, CITIES_CSV)

    # 直接入库（后续清洗POI时需要城市ID映射）
    db = DatabaseManager()
    db.connect()
    city_id_map = db.insert_cities(cleaned_cities)

    logger.info(f"城市数据爬取完成，共 {len(cleaned_cities)} 个城市")
    return cleaned_cities


def step_pois(args):
    """步骤2：爬取POI数据"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("步骤2: 爬取POI数据")
    logger.info("=" * 50)

    # 先获取城市列表
    crawler = CityCrawler()
    cities = crawler.get_target_cities(args.cities if args.cities else None)

    if not cities:
        logger.error("未获取到城市数据，无法爬取POI")
        return {}

    # 确定要爬取的POI类型
    poi_types = POI_TYPES
    if args.poi_types:
        poi_types = {k: v for k, v in POI_TYPES.items() if k in args.poi_types}

    logger.info(f"目标城市: {[c['name'] for c in cities]}")
    logger.info(f"POI类型: {list(poi_types.keys())}")

    # 爬取POI数据
    poi_crawler = PoiCrawler()
    all_pois = poi_crawler.crawl_all_cities(cities, poi_types)

    # 保存原始POI数据到CSV
    csv_paths = {
        "scenic_spots": SCENIC_SPOTS_CSV,
        "hotels": HOTELS_CSV,
        "restaurants": RESTAURANTS_CSV,
    }

    for table_name, pois in all_pois.items():
        if pois:
            csv_path = csv_paths.get(table_name)
            if csv_path:
                save_to_csv(pois, csv_path)

    logger.info(f"POI数据爬取完成！")
    for table_name, pois in all_pois.items():
        logger.info(f"  {table_name}: {len(pois)} 条")

    return all_pois


def step_clean(args):
    """步骤3：清洗数据"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("步骤3: 清洗POI数据")
    logger.info("=" * 50)

    cleaner = DataCleaner()
    db = DatabaseManager()
    db.connect()

    # 获取城市ID映射 {城市名: id}
    session = db.get_session()
    from models import City as CityModel
    cities = session.query(CityModel).all()
    city_id_map = {city.name: city.id for city in cities}
    session.close()

    if not city_id_map:
        logger.error("数据库中无城市数据，请先执行 step cities")
        return {}

    # 读取原始CSV数据并清洗
    csv_files = {
        "scenic_spots": SCENIC_SPOTS_CSV,
        "hotels": HOTELS_CSV,
        "restaurants": RESTAURANTS_CSV,
    }

    cleaned_data = {}

    for table_name, csv_path in csv_files.items():
        if not os.path.exists(csv_path):
            logger.warning(f"文件不存在，跳过: {csv_path}")
            continue

        # 读取CSV
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            raw_pois = list(reader)

        if not raw_pois:
            continue

        # 按城市分组清洗（因为全国数据中每行属于不同城市）
        all_cleaned = []
        city_groups = {}
        for poi in raw_pois:
            city_name = poi.get("_city_name", "")
            city_groups.setdefault(city_name, []).append(poi)

        for city_name, city_pois in city_groups.items():
            city_id = city_id_map.get(city_name)
            if city_id is None:
                logger.warning(f"城市 '{city_name}' 未在数据库中找到，跳过该城市的数据")
                continue

            cleaned = cleaner.clean_poi_list(city_pois, table_name, city_id)
            all_cleaned.extend(cleaned)

        cleaned_data[table_name] = all_cleaned

        # 保存清洗后的数据
        cleaned_csv = csv_path.replace(".csv", "_cleaned.csv")
        save_to_csv(all_cleaned, cleaned_csv)

    logger.info("数据清洗完成！")
    return cleaned_data


def step_load(args):
    """步骤4：将清洗后的数据导入数据库"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("步骤4: 数据入库")
    logger.info("=" * 50)

    db = DatabaseManager()
    db.connect()

    # 读取清洗后的CSV数据并入库
    csv_files = {
        "scenic_spots": (SCENIC_SPOTS_CSV.replace(".csv", "_cleaned.csv"), ScenicSpot),
        "hotels": (HOTELS_CSV.replace(".csv", "_cleaned.csv"), Hotel),
        "restaurants": (RESTAURANTS_CSV.replace(".csv", "_cleaned.csv"), Restaurant),
    }

    for table_name, (csv_path, model) in csv_files.items():
        if not os.path.exists(csv_path):
            logger.warning(f"清洗后的数据文件不存在，跳过: {csv_path}")
            continue

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            data = list(reader)

        # 清洗后的数据从CSV读取时全是字符串，需要转换类型
        numeric_fields = ["city_id", "score", "price", "price_level"]
        for row in data:
            for key in numeric_fields:
                if key in row:
                    if row[key] == "" or row[key] is None:
                        row[key] = None
                    else:
                        try:
                            row[key] = int(row[key]) if key == "city_id" else float(row[key])
                        except (ValueError, TypeError):
                            row[key] = None

        db.insert_pois(model, data)

    logger.info("数据入库完成！")


def step_verify(args):
    """步骤5：验证数据"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("步骤5: 数据验证")
    logger.info("=" * 50)

    db = DatabaseManager()
    db.connect()
    stats = db.verify_data()

    logger.info("\n" + "=" * 50)
    logger.info("数据验证结果:")
    logger.info("=" * 50)
    for name, count in stats.items():
        logger.info(f"  {name}: {count}")

    return stats


def step_enrich(args):
    """步骤：POI详情补全（评分/价格/营业时间）"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("步骤: POI详情补全")
    logger.info("=" * 50)

    updater = PoiDetailUpdater()
    result = updater.enrich_all_cities()

    logger.info(f"\n补全结果: 共更新 {result['total_updated']} 条POI记录")
    return result


def step_migrate(args):
    """步骤6：将 SQLite 数据迁移到 MySQL"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("步骤6: 迁移数据 SQLite → MySQL")
    logger.info("=" * 50)

    # 连接 SQLite 读取数据
    db_sqlite = DatabaseManager(db_type="sqlite")
    db_sqlite.connect()

    # MySQL 配置
    mysql_config = {
        "host": args.mysql_host or DB_HOST,
        "port": args.mysql_port or DB_PORT,
        "user": args.mysql_user or DB_USER,
        "password": args.mysql_password or DB_PASSWORD,
        "database": args.mysql_database or DB_NAME,
    }

    logger.info(f"MySQL 目标: {mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}")

    db_sqlite.migrate_to_mysql(mysql_config)


def step_all(args):
    """一键执行全部流程"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("开始执行完整数据工程流程")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)

    # 步骤0: 初始化数据库
    step_init_db(args)

    # 步骤1: 爬取城市
    step_cities(args)

    # 步骤2: 爬取POI
    step_pois(args)

    # 步骤3: 清洗数据
    step_clean(args)

    # 步骤4: 数据入库
    step_load(args)

    # 步骤5: 验证数据
    step_verify(args)

    logger.info("\n" + "=" * 50)
    logger.info("完整流程执行完毕！")
    logger.info("=" * 50)


# ============================================================
# 命令行入口
# ============================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="行知 - 数据工程模块",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 初始化数据库
  python main.py --step init_db

  # 爬取城市数据
  python main.py --step cities --cities 北京 上海 成都

  # 爬取所有POI数据
  python main.py --step pois

  # 只爬取景点数据
  python main.py --step pois --poi-types 景点

  # 清洗数据
  python main.py --step clean

  # 数据入库
  python main.py --step load

  # 验证数据
  python main.py --step verify

  # 将 SQLite 数据迁移到 MySQL
  python main.py --step migrate

  # 指定 MySQL 连接参数迁移
  python main.py --step migrate --mysql-host 192.168.1.100 --mysql-password mypwd

  # 一键执行全部流程
  python main.py --step all
        """,
    )

    parser.add_argument(
        "--step",
        type=str,
        choices=["init_db", "cities", "pois", "clean", "load", "verify", "enrich", "migrate", "all"],
        default="all",
        help="要执行的步骤 (默认: all)",
    )
    parser.add_argument(
        "--cities",
        type=str,
        nargs="+",
        default=None,
        help="目标城市列表，空格分隔 (默认: 使用 config.py 中的配置)",
    )
    parser.add_argument(
        "--poi-types",
        type=str,
        nargs="+",
        default=None,
        choices=["景点", "酒店", "餐饮服务"],
        help="POI类型列表，空格分隔 (默认: 爬取所有类型)",
    )
    parser.add_argument(
        "--mysql-host",
        type=str,
        default=None,
        help="MySQL 主机地址 (迁移时使用)",
    )
    parser.add_argument(
        "--mysql-port",
        type=int,
        default=None,
        help="MySQL 端口 (迁移时使用)",
    )
    parser.add_argument(
        "--mysql-user",
        type=str,
        default=None,
        help="MySQL 用户名 (迁移时使用)",
    )
    parser.add_argument(
        "--mysql-password",
        type=str,
        default=None,
        help="MySQL 密码 (迁移时使用)",
    )
    parser.add_argument(
        "--mysql-database",
        type=str,
        default=None,
        help="MySQL 数据库名 (迁移时使用)",
    )
    parser.add_argument(
        "--no-baidu",
        action="store_true",
        default=False,
        help="POI详情补全时，不使用百度地图API降级",
    )

    args = parser.parse_args()

    # 设置日志
    setup_logging()

    # 执行对应步骤
    step_map = {
        "init_db": step_init_db,
        "cities": step_cities,
        "pois": step_pois,
        "clean": step_clean,
        "load": step_load,
        "verify": step_verify,
        "enrich": step_enrich,
        "migrate": step_migrate,
        "all": step_all,
    }

    step_func = step_map[args.step]
    step_func(args)


if __name__ == "__main__":
    main()