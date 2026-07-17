"""本地 MySQL → TiDB Cloud 数据迁移脚本"""
import pymysql

SRC = dict(host="localhost", user="root", password="", database="xingzhi", charset="utf8mb4")

DST_SSL = {"fake_flag": True}

TABLES = [
    "cities", "scenic_spots", "hotels", "restaurants",  # 无 FK 依赖
    "users",                                              # FK 依赖的父表
    "favorites", "reviews", "travel_plans", "user_preference", "ai_sessions",  # FK 子表
]


def migrate():
    src = pymysql.connect(**SRC)
    dst = pymysql.connect(
        host="gateway01.ap-northeast-1.prod.aws.tidbcloud.com",
        port=4000,
        user="2Erny1PcLAcZciH.root",
        password="3BPfiTHElZ9VWYji",
        database="test",
        ssl=DST_SSL,
    )

    print("[已连接] 本地 MySQL → TiDB Cloud")

    src_cur = src.cursor()
    dst_cur = dst.cursor()

    dst_cur.execute("CREATE DATABASE IF NOT EXISTS xingzhi")
    dst_cur.execute("USE xingzhi")
    dst.commit()
    print("[已创建] 数据库 xingzhi")

    for table in TABLES:
        # 获取表结构
        try:
            src_cur.execute(f"SHOW CREATE TABLE {table}")
            create_sql = src_cur.fetchone()[1]
        except Exception:
            print(f"  [跳过] {table}: 本地表不存在")
            continue

        # 在 TiDB 建表
        create_sql = create_sql.replace(" AUTO_INCREMENT=", " /*!AUTO_INCREMENT=")
        create_sql = create_sql.replace(" DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci", "")
        create_sql = create_sql.replace(" COLLATE=utf8mb4_unicode_ci", "")

        # 尝试删旧表，失败则 truncate
        try:
            dst_cur.execute(f"DROP TABLE IF EXISTS {table}")
            dst_cur.execute(create_sql)
        except Exception:
            dst.rollback()
            try:
                dst_cur.execute(f"TRUNCATE TABLE {table}")
            except Exception as e2:
                print(f"  [警告] {table} 无法重建: {e2}")
                continue

        # 获取数据行数
        src_cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = src_cur.fetchone()[0]

        if count == 0:
            print(f"  {table}: 0 行（跳过）")
            continue

        # 分批读取 + 插入
        src_cur.execute(f"SELECT * FROM {table}")
        batch = []
        total = 0
        while True:
            row = src_cur.fetchone()
            if row is None:
                break
            batch.append(row)
            if len(batch) >= 500:
                placeholders = ",".join(["(" + ",".join(["%s"] * len(batch[0])) + ")"] * len(batch))
                flat = [v for r in batch for v in r]
                dst_cur.execute(f"INSERT INTO {table} VALUES {placeholders}", flat)
                total += len(batch)
                batch = []

        # 剩余批次
        if batch:
            placeholders = ",".join(["(" + ",".join(["%s"] * len(batch[0])) + ")"] * len(batch))
            flat = [v for r in batch for v in r]
            dst_cur.execute(f"INSERT INTO {table} VALUES {placeholders}", flat)
            total += len(batch)

        dst.commit()
        print(f"  {table}: {total} 行 OK")

    # 重置自增
    dst_cur.execute("ALTER TABLE cities AUTO_INCREMENT = 417")
    dst_cur.execute("ALTER TABLE scenic_spots AUTO_INCREMENT = 10324")
    dst_cur.execute("ALTER TABLE hotels AUTO_INCREMENT = 9728")
    dst_cur.execute("ALTER TABLE restaurants AUTO_INCREMENT = 7506")
    dst.commit()

    print("\n[完成] 数据迁移成功！")

    # 验证
    dst_cur.execute("USE xingzhi")
    for t in TABLES:
        dst_cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  TiDB.{t}: {dst_cur.fetchone()[0]} 行")

    src.close()
    dst.close()


if __name__ == "__main__":
    migrate()
