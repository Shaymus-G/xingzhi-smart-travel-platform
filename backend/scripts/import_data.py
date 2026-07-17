"""
SQLite → MySQL 数据导入脚本

功能：
  将数据组提供的 SQLite 数据库（xingzhi.db）中的旅游数据，
  清洗转换后导入到 MySQL 数据库。

使用方式：
  cd backend
  python scripts/import_data.py

  可选参数：
    --sqlite <path>    SQLite 文件路径（默认 ../docs/xingzhi.db）
    --clear            导入前清空 MySQL 表（默认不清空）
    --dry-run          只检查不写入

数据映射说明：
  - restaurants.type     → restaurants.category  （字段重命名）
  - cities.lat/lng       → VARCHAR → DECIMAL     （类型转换）
  - cities               → 自动生成 level 字段    （热门/普通/小众）
  - scenic_spots         → tags_json 留空          （AI标签待补充）
"""
import sys
import os
import argparse
import sqlite3
from typing import Optional

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine
from app.models.city import City
from app.models.scenic import ScenicSpot
from app.models.hotel import Hotel
from app.models.restaurant import Restaurant


# ==================== 转换函数 ====================

def safe_float(value) -> Optional[float]:
    """将字符串或数字安全转为 float，失败返回 None"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_str(value, max_len: int = None) -> Optional[str]:
    """安全转为字符串，空字符串视为 None"""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s == "[]":
        return None
    if max_len and len(s) > max_len:
        s = s[:max_len]
    return s


def determine_city_level(scenic_count: int) -> str:
    """根据景点数量确定城市等级"""
    if scenic_count >= 25:
        return "热门"
    elif scenic_count >= 15:
        return "普通"
    else:
        return "小众"


# ==================== 主导入逻辑 ====================

def import_data(sqlite_path: str, clear_first: bool = False, dry_run: bool = False):
    """主导入函数"""

    # --- 连接 SQLite ---
    if not os.path.exists(sqlite_path):
        print(f"[错误] SQLite 文件不存在: {sqlite_path}")
        sys.exit(1)

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    print(f"[OK] 已连接 SQLite: {sqlite_path}")

    if dry_run:
        print("[DRY RUN] 只检查数据格式，不写入 MySQL\n")

    # --- 连接 MySQL ---
    if not dry_run:
        db = SessionLocal()
        print("[OK] 已连接 MySQL\n")

    try:
        # ============ 1. 导入 cities ============
        print("=" * 60)
        print("[1/4] 导入城市数据 (cities)...")

        if clear_first and not dry_run:
            db.query(City).delete()
            db.commit()

        cities_data = sqlite_conn.execute("SELECT * FROM cities").fetchall()
        city_id_map = {}  # 旧 ID → 新 ID 映射（此处保持一致）
        city_scenic_counts = {}

        # 先统计每个城市的景点数，用于确定 level
        count_rows = sqlite_conn.execute(
            "SELECT city_id, COUNT(*) as cnt FROM scenic_spots GROUP BY city_id"
        ).fetchall()
        for row in count_rows:
            city_scenic_counts[row["city_id"]] = row["cnt"]

        imported = 0
        for row in cities_data:
            scenic_count = city_scenic_counts.get(row["id"], 0)
            city = City(
                id=row["id"],  # 保持原 ID，确保外键关联不丢失
                name=safe_str(row["name"], 100),
                province=safe_str(row["province"], 50) or "未知",
                country=safe_str(row["country"], 50) or "中国",
                description=safe_str(row["description"], 2000),
                cover_image=safe_str(row["cover_image"], 500),
                latitude=safe_float(row["latitude"]),
                longitude=safe_float(row["longitude"]),
                level=determine_city_level(scenic_count),
            )
            if not dry_run:
                db.add(city)
            imported += 1

        if not dry_run:
            db.commit()
        print(f"  导入城市: {imported} 条")

        # ============ 2. 导入 scenic_spots ============
        print("[2/4] 导入景点数据 (scenic_spots)...")

        if clear_first and not dry_run:
            db.query(ScenicSpot).delete()
            db.commit()

        spots_data = sqlite_conn.execute("SELECT * FROM scenic_spots").fetchall()
        imported = 0
        for row in spots_data:
            spot = ScenicSpot(
                id=row["id"],
                city_id=row["city_id"],
                name=safe_str(row["name"], 100),
                description=safe_str(row["description"], 5000),
                address=safe_str(row["address"], 500),
                category=safe_str(row["category"], 50),
                score=safe_float(row["score"]),
                price=safe_float(row["price"]),
                open_time=safe_str(row["open_time"], 100),
                latitude=safe_float(row["latitude"]),
                longitude=safe_float(row["longitude"]),
                image_url=safe_str(row["image_url"], 500),
                tags_json=None,  # SQLite 无此字段，后续 AI 组补充
            )
            if not dry_run:
                db.add(spot)
            imported += 1

        if not dry_run:
            db.commit()
        print(f"  导入景点: {imported} 条")

        # ============ 3. 导入 hotels ============
        print("[3/4] 导入酒店数据 (hotels)...")

        if clear_first and not dry_run:
            db.query(Hotel).delete()
            db.commit()

        hotels_data = sqlite_conn.execute("SELECT * FROM hotels").fetchall()
        imported = 0
        for row in hotels_data:
            hotel = Hotel(
                id=row["id"],
                city_id=row["city_id"],
                name=safe_str(row["name"], 100),
                description=safe_str(row["description"], 5000),
                address=safe_str(row["address"], 500),
                price=safe_float(row["price"]),
                score=safe_float(row["score"]),
                open_time=safe_str(row["open_time"], 100),
                latitude=safe_float(row["latitude"]),
                longitude=safe_float(row["longitude"]),
                image_url=safe_str(row["image_url"], 500),
            )
            if not dry_run:
                db.add(hotel)
            imported += 1

        if not dry_run:
            db.commit()
        print(f"  导入酒店: {imported} 条")

        # ============ 4. 导入 restaurants ============
        print("[4/4] 导入餐厅数据 (restaurants)...")

        if clear_first and not dry_run:
            db.query(Restaurant).delete()
            db.commit()

        rest_data = sqlite_conn.execute("SELECT * FROM restaurants").fetchall()
        imported = 0
        for row in rest_data:
            # 价格等级映射: FLOAT → VARCHAR
            price_map = {1: "低", 2: "中", 3: "高"}
            price_level = None
            if row["price_level"] is not None:
                try:
                    level_int = int(float(row["price_level"]))
                    price_level = price_map.get(level_int, str(level_int))
                except (ValueError, TypeError):
                    price_level = str(row["price_level"])

            restaurant = Restaurant(
                id=row["id"],
                city_id=row["city_id"],
                name=safe_str(row["name"], 100),
                category=safe_str(row["type"], 50),  # ← SQLite 的 type → MySQL 的 category
                description=safe_str(row["description"], 5000),
                price_level=price_level,
                score=safe_float(row["score"]),
                address=safe_str(row["address"], 500),
                latitude=safe_float(row["latitude"]),
                longitude=safe_float(row["longitude"]),
                image_url=safe_str(row["image_url"], 500),
            )
            if not dry_run:
                db.add(restaurant)
            imported += 1

        if not dry_run:
            db.commit()
        print(f"  导入餐厅: {imported} 条")

        # ============ 5. 重置自增序列 ============
        if not dry_run:
            print("\n[收尾] 重置自增 ID 序列...")
            from sqlalchemy import text
            tables = ["cities", "scenic_spots", "hotels", "restaurants"]
            for table in tables:
                max_id = db.execute(
                    text(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}")
                ).scalar()
                db.execute(
                    text(f"ALTER TABLE {table} AUTO_INCREMENT = {max_id}")
                )
            db.commit()
            print("  完成")

    finally:
        sqlite_conn.close()
        if not dry_run:
            db.close()

    # ============ 汇总 ============
    print("\n" + "=" * 60)
    print("导入完成！")

    if not dry_run:
        # 验证
        db2 = SessionLocal()
        try:
            from sqlalchemy import text
            tables = ["cities", "scenic_spots", "hotels", "restaurants"]
            for t in tables:
                count = db2.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                print(f"  {t}: {count} 条")
        finally:
            db2.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite → MySQL 数据导入")
    parser.add_argument(
        "--sqlite",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "docs", "xingzhi.db"),
        help="SQLite 数据库文件路径",
    )
    parser.add_argument("--clear", action="store_true", help="导入前清空 MySQL 表")
    parser.add_argument("--dry-run", action="store_true", help="只检查不写入")
    args = parser.parse_args()

    import_data(
        sqlite_path=os.path.abspath(args.sqlite),
        clear_first=args.clear,
        dry_run=args.dry_run,
    )
