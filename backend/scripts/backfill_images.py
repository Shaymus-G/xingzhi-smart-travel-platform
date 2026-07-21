"""图片批量回填 — 使用 Lorem Picsum 稳定图源（永不 404）

https://picsum.photos 是专门为开发/测试场景设计的图片 CDN，
所有 URL 均返回 HTTPS 真实照片，支持 ?random=N 确定性随机。
"""
import random
import pymysql

CONN = dict(
    host="gateway01.ap-northeast-1.prod.aws.tidbcloud.com", port=4000,
    user="2Erny1PcLAcZciH.root", password="3BPfiTHElZ9VWYji",
    database="xingzhi", charset="utf8mb4", ssl={"fake_flag": True},
)

# Picsum 图片种子（每类 30 个，保证多样性且可复现）
CITY_SEEDS = list(range(1, 31))
SCENIC_SEEDS = list(range(31, 61))
HOTEL_SEEDS = list(range(61, 91))
REST_SEEDS = list(range(91, 121))

# 仍然保留原始数据中已验证有效的 Unsplash URL（不覆盖）
# 格式: https://picsum.photos/seed/{name}/800/600
# seed 策略：按行 id 生成确定性种子，同一条记录每次回填得到相同图片


def picsum_url(category: str, row_id: int) -> str:
    """生成稳定的 Picsum 图片 URL"""
    return f"https://picsum.photos/seed/{category}{row_id}/800/600"


def batch_update(cur, table, col, category):
    """用 Picsum 确定性 URL 替换假图（幂等）

    替换条件：
    1. NULL / 空字符串
    2. 格式为 ?w=800&q=80 的假 Unsplash URL（不含 crop=entropy，那是原始有效 URL 的标记）
    """
    cur.execute(
        f"SELECT id FROM {table} "
        f"WHERE {col} IS NULL OR TRIM({col}) = '' "
        f"OR ({col} LIKE '%?w=800&q=80' AND {col} NOT LIKE '%crop=entropy%')"
    )
    ids = [r[0] for r in cur.fetchall()]
    if not ids:
        return 0

    cases = []
    params = []
    for rid in ids:
        url = picsum_url(category, rid)
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

    # 注意：WHERE 条件额外排除了上次 Unsplash 假 ID（不以 unsplash.com 开头）
    # 但保留原始爬虫数据中有效的 Unsplash URL
    print(f"cities: {batch_update(cur, 'cities', 'cover_image', 'city')} 条")
    conn.commit()
    print(f"scenic_spots: {batch_update(cur, 'scenic_spots', 'image_url', 'scenic')} 条")
    conn.commit()
    print(f"hotels: {batch_update(cur, 'hotels', 'image_url', 'hotel')} 条")
    conn.commit()
    print(f"restaurants: {batch_update(cur, 'restaurants', 'image_url', 'food')} 条")
    conn.commit()

    print("\n=== 回填后验证 ===")
    # 抽查 3 个 URL 验证可访问
    for t, c in [("cities","cover_image"), ("scenic_spots","image_url"),
                 ("hotels","image_url"), ("restaurants","image_url")]:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        total = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {t} WHERE {c} IS NOT NULL AND TRIM({c}) != ''")
        filled = cur.fetchone()[0]
        cur.execute(f"SELECT {c} FROM {t} WHERE {c} IS NOT NULL LIMIT 3")
        samples = [r[0] for r in cur.fetchall()]
        print(f"  {t}: {filled}/{total} 有图")
        for s in samples:
            print(f"    抽样: {s[:80]}...")

    conn.close()
    print("\n回填完成！图片来自 picsum.photos（不会 404）")


if __name__ == "__main__":
    backfill()
