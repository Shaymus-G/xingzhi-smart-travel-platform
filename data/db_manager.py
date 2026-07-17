"""
数据库管理模块

负责数据库连接、建表、数据插入等操作。
支持 SQLite（开发测试）和 MySQL（生产环境）两种模式。
"""

import logging
import os
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from config import DB_TYPE, DB_PATH, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DATA_DIR
from models import Base, get_all_tables, City, ScenicSpot, Hotel, Restaurant

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_type: str = None):
        self.db_type = db_type or DB_TYPE
        self.engine = None

    def get_connection_url(self) -> str:
        """
        获取数据库连接URL

        Returns:
            SQLAlchemy 连接URL
        """
        if self.db_type == "mysql":
            return (
                f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
                f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
            )
        else:
            # 默认使用 SQLite
            db_dir = os.path.dirname(DB_PATH)
            os.makedirs(db_dir, exist_ok=True)
            return f"sqlite:///{DB_PATH}"

    def connect(self):
        """建立数据库连接"""
        url = self.get_connection_url()
        logger.info(f"连接数据库: {self.db_type}://{self._mask_url(url)}")

        if self.db_type == "sqlite":
            self.engine = create_engine(url, echo=False)
        else:
            self.engine = create_engine(url, echo=False, pool_size=5, max_overflow=10)

        logger.info("数据库连接成功")

    def _mask_url(self, url: str) -> str:
        """隐藏密码信息"""
        if "@" in url:
            parts = url.split("@")
            return parts[0].split(":")[0] + ":****@" + parts[1]
        return url

    def create_tables(self):
        """创建所有表（如果不存在）"""
        if not self.engine:
            self.connect()
        logger.info("正在创建数据库表...")
        Base.metadata.create_all(self.engine)
        logger.info("数据库表创建完成")

    def get_session(self) -> Session:
        """获取数据库会话"""
        if not self.engine:
            self.connect()
        return Session(self.engine)

    def insert_cities(self, cities: list) -> dict:
        """
        批量插入城市数据

        Args:
            cities: 清洗后的城市数据列表

        Returns:
            {city_name: city_id} 的映射字典
        """
        if not cities:
            return {}

        session = self.get_session()
        city_id_map = {}

        try:
            for city_data in cities:
                # 检查是否已存在同名城市
                existing = (
                    session.query(City)
                    .filter(City.name == city_data["name"])
                    .first()
                )
                if existing:
                    city_id_map[city_data["name"]] = existing.id
                    logger.debug(f"城市 '{city_data['name']}' 已存在，ID={existing.id}")
                    continue

                city = City(**city_data)
                session.add(city)
                session.flush()  # 立即获取自增ID
                city_id_map[city_data["name"]] = city.id
                logger.debug(f"新增城市: {city_data['name']} -> ID={city.id}")

            session.commit()
            logger.info(f"城市数据插入完成: {len(city_id_map)} 个城市")

        except Exception as e:
            session.rollback()
            logger.error(f"插入城市数据失败: {e}")
            raise
        finally:
            session.close()

        return city_id_map

    def insert_pois(self, table_model, pois: list, batch_size: int = 50):
        """
        批量插入POI数据

        Args:
            table_model: SQLAlchemy 模型类 (ScenicSpot / Hotel / Restaurant)
            pois: 清洗后的POI数据列表
            batch_size: 每批插入数量
        """
        if not pois:
            logger.info(f"{table_model.__tablename__}: 没有数据需要插入")
            return

        session = self.get_session()
        total = 0

        try:
            for i in range(0, len(pois), batch_size):
                batch = pois[i : i + batch_size]
                for poi_data in batch:
                    poi = table_model(**poi_data)
                    session.add(poi)
                session.flush()
                total += len(batch)
                logger.debug(f"  已插入 {total}/{len(pois)} 条")

            session.commit()
            logger.info(
                f"{table_model.__tablename__}: 共插入 {total} 条数据"
            )

        except Exception as e:
            session.rollback()
            logger.error(f"插入 {table_model.__tablename__} 数据失败: {e}")
            raise
        finally:
            session.close()

    def verify_data(self) -> dict:
        """
        验证数据库中的数据

        Returns:
            各表的数据量统计信息
        """
        session = self.get_session()
        stats = {}

        try:
            table_names = {
                "cities": City,
                "scenic_spots": ScenicSpot,
                "hotels": Hotel,
                "restaurants": Restaurant,
            }

            for name, model in table_names.items():
                count = session.query(model).count()
                stats[name] = count
                logger.info(f"  {name}: {count} 条记录")

            # 额外检查：城市是否关联了POI数据
            if stats.get("cities", 0) > 0:
                city_with_spots = (
                    session.query(City)
                    .join(ScenicSpot, City.id == ScenicSpot.city_id)
                    .distinct()
                    .count()
                )
                city_with_hotels = (
                    session.query(City)
                    .join(Hotel, City.id == Hotel.city_id)
                    .distinct()
                    .count()
                )
                city_with_restaurants = (
                    session.query(City)
                    .join(Restaurant, City.id == Restaurant.city_id)
                    .distinct()
                    .count()
                )
                stats["cities_with_scenic_spots"] = city_with_spots
                stats["cities_with_hotels"] = city_with_hotels
                stats["cities_with_restaurants"] = city_with_restaurants

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
        finally:
            session.close()

        return stats

    def migrate_to_mysql(self, mysql_config: dict):
        """
        将 SQLite 中的数据迁移到 MySQL

        Args:
            mysql_config: MySQL 连接配置字典
                {
                    "host": "localhost",
                    "port": 3306,
                    "user": "root",
                    "password": "...",
                    "database": "xingzhi"
                }
        """
        from sqlalchemy import create_engine as ce

        logger.info("=" * 50)
        logger.info("开始迁移: SQLite → MySQL")
        logger.info("=" * 50)

        # 1. 从 SQLite 读取数据
        logger.info("正在从 SQLite 读取数据...")
        session_src = self.get_session()

        # 按顺序读取（先读城市，再读依赖城市的POI数据）
        cities_data = []
        spots_data = []
        hotels_data = []
        restaurants_data = []

        try:
            for city in session_src.query(City).all():
                cities_data.append({
                    "id": city.id,
                    "name": city.name,
                    "province": city.province,
                    "country": city.country,
                    "description": city.description,
                    "cover_image": city.cover_image,
                    "latitude": city.latitude,
                    "longitude": city.longitude,
                })

            for spot in session_src.query(ScenicSpot).all():
                spots_data.append({
                    "city_id": spot.city_id,
                    "name": spot.name,
                    "description": spot.description,
                    "address": spot.address,
                    "category": spot.category,
                    "score": spot.score,
                    "price": spot.price,
                    "open_time": spot.open_time,
                    "latitude": spot.latitude,
                    "longitude": spot.longitude,
                    "image_url": spot.image_url,
                })

            for hotel in session_src.query(Hotel).all():
                hotels_data.append({
                    "city_id": hotel.city_id,
                    "name": hotel.name,
                    "description": hotel.description,
                    "address": hotel.address,
                    "price": hotel.price,
                    "score": hotel.score,
                    "open_time": hotel.open_time,
                    "latitude": hotel.latitude,
                    "longitude": hotel.longitude,
                    "image_url": hotel.image_url,
                })

            for rest in session_src.query(Restaurant).all():
                restaurants_data.append({
                    "city_id": rest.city_id,
                    "name": rest.name,
                    "type": rest.type,
                    "description": rest.description,
                    "price_level": rest.price_level,
                    "score": rest.score,
                    "address": rest.address,
                    "latitude": rest.latitude,
                    "longitude": rest.longitude,
                    "image_url": rest.image_url,
                })

        finally:
            session_src.close()

        logger.info(f"从 SQLite 读取完成: 城市={len(cities_data)}, "
                    f"景点={len(spots_data)}, 酒店={len(hotels_data)}, "
                    f"餐饮={len(restaurants_data)}")

        # 2. 连接 MySQL
        mysql_url = (
            f"mysql+pymysql://{mysql_config['user']}:{mysql_config['password']}"
            f"@{mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}"
            f"?charset=utf8mb4"
        )
        logger.info(f"连接 MySQL: {mysql_config['host']}:{mysql_config['port']}/{mysql_config['database']}")

        engine_mysql = ce(mysql_url, echo=False)
        Base.metadata.create_all(engine_mysql)
        logger.info("MySQL 表结构创建完成")

        # 3. 写入 MySQL
        session_dst = Session(engine_mysql)

        try:
            # 先插入城市，建立 id 映射
            logger.info("正在写入城市数据...")
            city_id_map = {}
            for city_data in cities_data:
                old_id = city_data.pop("id")
                existing = session_dst.query(City).filter(City.name == city_data["name"]).first()
                if existing:
                    city_id_map[old_id] = existing.id
                    continue
                city = City(**city_data)
                session_dst.add(city)
                session_dst.flush()
                city_id_map[old_id] = city.id

            # 更新 POI 数据中的 city_id 为新 ID
            for data_list in [spots_data, hotels_data, restaurants_data]:
                for item in data_list:
                    old_city_id = item["city_id"]
                    item["city_id"] = city_id_map.get(old_city_id, old_city_id)

            # 写入景点
            logger.info("正在写入景点数据...")
            for i in range(0, len(spots_data), 50):
                batch = spots_data[i:i + 50]
                for item in batch:
                    session_dst.add(ScenicSpot(**item))
                session_dst.flush()

            # 写入酒店
            logger.info("正在写入酒店数据...")
            for i in range(0, len(hotels_data), 50):
                batch = hotels_data[i:i + 50]
                for item in batch:
                    session_dst.add(Hotel(**item))
                session_dst.flush()

            # 写入餐饮
            logger.info("正在写入餐饮数据...")
            for i in range(0, len(restaurants_data), 50):
                batch = restaurants_data[i:i + 50]
                for item in batch:
                    session_dst.add(Restaurant(**item))
                session_dst.flush()

            session_dst.commit()
            logger.info("数据迁移完成！")

            # 验证
            for name, model in [("cities", City), ("scenic_spots", ScenicSpot),
                                ("hotels", Hotel), ("restaurants", Restaurant)]:
                count = session_dst.query(model).count()
                logger.info(f"  MySQL {name}: {count} 条")

        except Exception as e:
            session_dst.rollback()
            logger.error(f"迁移失败: {e}")
            raise
        finally:
            session_dst.close()