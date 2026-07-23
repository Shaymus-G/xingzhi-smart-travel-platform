"""P4 新表导入：娱乐场所 + 商场 → TiDB Cloud"""
import sqlite3, pymysql, random

SRC = "c:/Users/guoju/Desktop/实习实训/文旅助手/code/docs/xingzhi.db"
DST = dict(host="gateway01.ap-northeast-1.prod.aws.tidbcloud.com", port=4000,
    user="2Erny1PcLAcZciH.root", password="3BPfiTHElZ9VWYji",
    database="xingzhi", charset="utf8mb4", ssl={"fake_flag": True})

PICSUM = "https://picsum.photos/seed/{}{}/800/600"

def safe_float(v):
    try: return float(v) if v else None
    except: return None

def safe_str(v, n=None):
    if not v: return None
    v = str(v).strip()
    if v in ("", "[]"): return None
    return v[:n] if n else v

def import_table(name, label):
    src = sqlite3.connect(SRC); src.row_factory = sqlite3.Row
    dst = pymysql.connect(**DST)
    sc = src.cursor(); dc = dst.cursor()

    dc.execute(f"""
        CREATE TABLE IF NOT EXISTS {name} (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            city_id BIGINT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            address VARCHAR(500),
            category VARCHAR(50),
            score DECIMAL(3,1),
            price DECIMAL(10,2),
            open_time VARCHAR(100),
            latitude DECIMAL(10,7),
            longitude DECIMAL(10,7),
            image_url VARCHAR(500),
            FOREIGN KEY (city_id) REFERENCES cities(id) ON DELETE CASCADE
        )
    """)
    dc.execute(f"DELETE FROM {name}")
    dst.commit()

    rows = sc.execute(f"SELECT * FROM {name}").fetchall()
    for i, r in enumerate(rows):
        img = PICSUM.format(label, i+1)
        dc.execute(f"INSERT INTO {name} (id,city_id,name,description,address,category,score,price,open_time,latitude,longitude,image_url) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (r["id"], r["city_id"], safe_str(r["name"],100), safe_str(r["description"]),
             safe_str(r["address"],500), safe_str(r["category"],50),
             safe_float(r["score"]), safe_float(r["price"]),
             safe_str(r["open_time"],100), safe_float(r["latitude"]), safe_float(r["longitude"]), img))
        if i % 50 == 0: dst.commit()

    dst.commit()
    dc.execute(f"SELECT COUNT(*) FROM {name}")
    cnt = dc.fetchone()[0]
    dc.execute(f"ALTER TABLE {name} AUTO_INCREMENT = {cnt+1}")
    dst.commit()
    print(f"{name}: {cnt} rows imported")

    src.close(); dst.close()

import_table("entertainments", "ent")
import_table("shopping_malls", "mall")
print("Done!")
