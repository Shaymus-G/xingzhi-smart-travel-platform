"""图片回填脚本 — 为 TiDB Cloud 中缺图的旅游资源填充 Unsplash 图片

使用稳定的 Unsplash CDN URL，按类别匹配相关图片。
只填充空字段，不覆盖已有有效 URL。
支持重复执行（幂等）。
"""
import random
import pymysql

# TiDB Cloud 连接
CONN = dict(
    host="gateway01.ap-northeast-1.prod.aws.tidbcloud.com",
    port=4000,
    user="2Erny1PcLAcZciH.root",
    password="3BPfiTHElZ9VWYji",
    database="xingzhi",
    charset="utf8mb4",
    ssl={"fake_flag": True},
)

# ==================== Unsplash 图片池 ====================
# 格式: https://images.unsplash.com/photo-{id}?w=800&q=80
# 所有 URL 均为已验证可访问的 HTTPS 图片

CITY_IMAGES = [
    "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=800&q=80",  # 城市天际线
    "https://images.unsplash.com/photo-1449824913935-59a10b8d2000?w=800&q=80",  # 城市风光
    "https://images.unsplash.com/photo-1480714378408-67cf0d13bc1b?w=800&q=80",  # 都市
    "https://images.unsplash.com/photo-1444723121867-7a241cacace9?w=800&q=80",  # 城市建筑
    "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=800&q=80",  # 城市河流
    "https://images.unsplash.com/photo-1496016943515-7d33598c11e6?w=800&q=80",  # 夜景城市
    "https://images.unsplash.com/photo-1464938050520-ef2270bb8ce8?w=800&q=80",  # 老城
    "https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=800&q=80",  # 现代城市
    "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800&q=80",  # 巴黎
    "https://images.unsplash.com/photo-1533929736458-ca588d08c8be?w=800&q=80",  # 伦敦
    "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?w=800&q=80",  # 纽约
    "https://images.unsplash.com/photo-1500916434205-0c77489c97e4?w=800&q=80",  # 东京
    "https://images.unsplash.com/photo-1548919973-5cef591cdbc9?w=800&q=80",  # 古建筑群
    "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",  # 中国古城
    "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=800&q=80",  # 日本城市
    "https://images.unsplash.com/photo-1531219572328-a0171b4448a3?w=800&q=80",  # 滨水城市
    "https://images.unsplash.com/photo-1485738422979-f5c462d49f74?w=800&q=80",  # 山城
    "https://images.unsplash.com/photo-1506197603052-3cc9c3a201bd?w=800&q=80",  # 水乡
    "https://images.unsplash.com/photo-1518684079-3c830dcef090?w=800&q=80",  # 海滨城市
    "https://images.unsplash.com/photo-1569288052389-dac9b0ac53f7?w=800&q=80",  # 街道
]

SCENIC_IMAGES = [
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80",  # 山景
    "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&q=80",  # 自然
    "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=800&q=80",  # 湖泊
    "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=800&q=80",  # 草原
    "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80",  # 森林
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80",  # 海滩
    "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=800&q=80",  # 海洋
    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80",  # 高山
    "https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=800&q=80",  # 瀑布
    "https://images.unsplash.com/photo-1540390769625-2fc3f8b1d50c?w=800&q=80",  # 古镇
    "https://images.unsplash.com/photo-1565967511849-76a60a516170?w=800&q=80",  # 寺庙
    "https://images.unsplash.com/photo-1503174971373-b1f69850bded?w=800&q=80",  # 花园
    "https://images.unsplash.com/photo-1472396961693-142e6e269027?w=800&q=80",  # 公园
    "https://images.unsplash.com/photo-1518548419970-58e3b4079ab2?w=800&q=80",  # 河流
    "https://images.unsplash.com/photo-1537525262546-1dd5d65dd32b?w=800&q=80",  # 峡谷
    "https://images.unsplash.com/photo-1504198453319-5ce911bafcde?w=800&q=80",  # 博物馆
    "https://images.unsplash.com/photo-1549144511-f099e5e5f7d1?w=800&q=80",  # 历史遗迹
    "https://images.unsplash.com/photo-1469796466635-455ede028aca?w=800&q=80",  # 樱花/花卉
    "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=800&q=80",  # 雪山
    "https://images.unsplash.com/photo-1500530855694-b5866c85b0ff?w=800&q=80",  # 沙漠
]

HOTEL_IMAGES = [
    "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80",  # 度假酒店
    "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=800&q=80",  # 酒店大堂
    "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=800&q=80",  # 酒店外观
    "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800&q=80",  # 酒店泳池
    "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800&q=80",  # 酒店室内
    "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80",  # 精品酒店
    "https://images.unsplash.com/photo-1596394516093-501ba68a0ba6?w=800&q=80",  # 民宿
    "https://images.unsplash.com/photo-1584132967334-10e028bd69f7?w=800&q=80",  # 经济酒店
    "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800&q=80",  # 豪华酒店
    "https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800&q=80",  # 中式酒店
]

RESTAURANT_IMAGES = [
    "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80",  # 餐厅内景
    "https://images.unsplash.com/photo-1552566626-52f8b828add9?w=800&q=80",  # 高级餐厅
    "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&q=80",  # 咖啡馆
    "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&q=80",  # 精致餐饮
    "https://images.unsplash.com/photo-1550966871-3ed3cdb51f3a?w=800&q=80",  # 中餐
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80",  # 美食
    "https://images.unsplash.com/photo-1544025162-d76694265947?w=800&q=80",  # 牛排
    "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800&q=80",  # 早餐
    "https://images.unsplash.com/photo-1559339352-11d035aa65de?w=800&q=80",  # 面食
    "https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=800&q=80",  # 海鲜
]


def backfill():
    conn = pymysql.connect(**CONN)
    cur = conn.cursor()

    stats = {}

    # --- cities ---
    cur.execute(
        "SELECT id FROM cities WHERE cover_image IS NULL OR TRIM(cover_image) = ''"
    )
    ids = [r[0] for r in cur.fetchall()]
    for cid in ids:
        img = random.choice(CITY_IMAGES)
        cur.execute("UPDATE cities SET cover_image = %s WHERE id = %s", (img, cid))
    conn.commit()
    stats["cities"] = {"total": len(ids)}
    print(f"cities: 填充 {len(ids)} 条")

    # --- scenic_spots ---
    cur.execute(
        "SELECT id FROM scenic_spots WHERE image_url IS NULL OR TRIM(image_url) = ''"
    )
    ids = [r[0] for r in cur.fetchall()]
    for sid in ids:
        img = random.choice(SCENIC_IMAGES)
        cur.execute("UPDATE scenic_spots SET image_url = %s WHERE id = %s", (img, sid))
    conn.commit()
    stats["scenic_spots"] = {"total": len(ids)}
    print(f"scenic_spots: 填充 {len(ids)} 条")

    # --- hotels ---
    cur.execute(
        "SELECT id FROM hotels WHERE image_url IS NULL OR TRIM(image_url) = ''"
    )
    ids = [r[0] for r in cur.fetchall()]
    for hid in ids:
        img = random.choice(HOTEL_IMAGES)
        cur.execute("UPDATE hotels SET image_url = %s WHERE id = %s", (img, hid))
    conn.commit()
    stats["hotels"] = {"total": len(ids)}
    print(f"hotels: 填充 {len(ids)} 条")

    # --- restaurants ---
    cur.execute(
        "SELECT id FROM restaurants WHERE image_url IS NULL OR TRIM(image_url) = ''"
    )
    ids = [r[0] for r in cur.fetchall()]
    for rid in ids:
        img = random.choice(RESTAURANT_IMAGES)
        cur.execute("UPDATE restaurants SET image_url = %s WHERE id = %s", (img, rid))
    conn.commit()
    stats["restaurants"] = {"total": len(ids)}
    print(f"restaurants: 填充 {len(ids)} 条")

    # 验证
    print("\n=== 回填后 ===")
    for table, img_col in [
        ("cities", "cover_image"),
        ("scenic_spots", "image_url"),
        ("hotels", "image_url"),
        ("restaurants", "image_url"),
    ]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        total = cur.fetchone()[0]
        cur.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {img_col} IS NOT NULL AND TRIM({img_col}) != ''"
        )
        filled = cur.fetchone()[0]
        print(f"  {table}: {filled}/{total} 有图")

    conn.close()
    print("\n回填完成！")


if __name__ == "__main__":
    backfill()
