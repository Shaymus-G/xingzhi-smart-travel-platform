"""图片批量回填 — 每条 UPDATE 句式更新整表，适合远程数据库"""
import random
import pymysql

CONN = dict(
    host="gateway01.ap-northeast-1.prod.aws.tidbcloud.com", port=4000,
    user="2Erny1PcLAcZciH.root", password="3BPfiTHElZ9VWYji",
    database="xingzhi", charset="utf8mb4", ssl={"fake_flag": True},
)

# 图片池（已验证 HTTPS URL）
def img(id): return f"https://images.unsplash.com/photo-{id}?w=800&q=80"

CITY_IDS = [1477959858617, 1449824913935, 1480714378408, 1444723121867, 1514565131,
            1496016943515, 1464938050520, 1519501025264, 1502602898657, 1533929736458,
            1496442226666, 1500916434205, 1548919973, 1548013146, 1545569341,
            1531219572328, 1485738422979, 1506197603052, 1518684079, 1569288052389]
SCENIC_IDS = [1506905925346, 1469474968028, 1501785888041, 1472214103451, 1441974231531,
              1507525428034, 1518837695005, 1464822759023, 1433086966358, 1540390769625,
              1565967511849, 1503174971373, 1472396961693, 1518548419970, 1537525262546,
              1504198453319, 1549144511, 1469796466635, 1519681393784, 1500530855694]
HOTEL_IDS = [1566073771259, 1582719508461, 1551882547, 1520250497591, 1571896349842,
             1590490360182, 1596394516093, 1584132967334, 1542314831, 1564501049412]
REST_IDS = [1517248135467, 1552566626, 1555396273, 1414235077428, 1550966871,
            1504674900247, 1544025162, 1567620905732, 1559339352, 1563379926898]


def batch_update(cur, table, col, image_ids):
    """批量更新：随机分配图片 URL（幂等，只更新空字段）"""
    cur.execute(f"SELECT id FROM {table} WHERE {col} IS NULL OR TRIM({col}) = ''")
    ids = [r[0] for r in cur.fetchall()]
    if not ids:
        return 0

    # 构建 CASE WHEN 批量 SQL
    cases = []
    params = []
    for rid in ids:
        photo_id = random.choice(image_ids)
        url = img(photo_id)
        cases.append(f"WHEN {rid} THEN %s")
        params.append(url)

    sql = f"""
        UPDATE {table} SET {col} = CASE id {' '.join(cases)} END
        WHERE id IN ({','.join(str(i) for i in ids)})
    """
    cur.execute(sql, params)
    return len(ids)


def backfill():
    conn = pymysql.connect(**CONN)
    cur = conn.cursor()

    print(f"cities: {batch_update(cur, 'cities', 'cover_image', CITY_IDS)} 条")
    conn.commit()
    print(f"scenic_spots: {batch_update(cur, 'scenic_spots', 'image_url', SCENIC_IDS)} 条")
    conn.commit()
    print(f"hotels: {batch_update(cur, 'hotels', 'image_url', HOTEL_IDS)} 条")
    conn.commit()
    print(f"restaurants: {batch_update(cur, 'restaurants', 'image_url', REST_IDS)} 条")
    conn.commit()

    print("\n=== 回填后验证 ===")
    for t, c in [("cities","cover_image"), ("scenic_spots","image_url"),
                 ("hotels","image_url"), ("restaurants","image_url")]:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        total = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {t} WHERE {c} IS NOT NULL AND TRIM({c}) != ''")
        filled = cur.fetchone()[0]
        print(f"  {t}: {filled}/{total} 有图")

    conn.close()
    print("\n回填完成！")


if __name__ == "__main__":
    backfill()
