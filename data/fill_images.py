"""
图片补充脚本

从数据库中读取没有图片的记录，通过 Pixabay API 搜索并填充图片URL。
策略：填充所有城市封面图 + 每个城市前3个景点图片。
"""

import os
import sys
import time
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import City, ScenicSpot
from pixabay_image_fetcher import PixabayImageFetcher
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_TYPE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# 热门城市专属关键词（英文，Pixabay搜索效果更好）
CITY_KEYWORDS = {
    "北京": "beijing forbidden city great wall",
    "上海": "shanghai bund skyline",
    "广州": "guangzhou city canton tower",
    "深圳": "shenzhen modern city",
    "成都": "chengdu panda city",
    "杭州": "hangzhou west lake",
    "南京": "nanjing confucius temple",
    "西安": "xian terracotta warriors",
    "重庆": "chongqing night city",
    "武汉": "wuhan yellow crane tower",
    "长沙": "changsha city",
    "苏州": "suzhou garden",
    "厦门": "xiamen island beach",
    "青岛": "qingdao beach sea",
    "大连": "dalian coastal city",
    "昆明": "kunming spring city",
    "拉萨": "lhasa potala palace tibet",
    "哈尔滨": "harbin ice festival",
    "三亚": "sanya tropical beach",
    "桂林": "guilin karst landscape river",
    "天津": "tianjin city",
    "济南": "jinan spring city",
    "郑州": "zhengzhou city",
    "沈阳": "shenyang city",
    "长春": "changchun city",
    "合肥": "hefei city",
    "福州": "fuzhou city",
    "南昌": "nanchang city",
    "贵阳": "guiyang city",
    "兰州": "lanzhou city",
    "呼和浩特": "hohhot grassland",
    "乌鲁木齐": "urumqi xinjiang",
    "银川": "yinchuan city",
    "西宁": "xining qinghai lake",
    "石家庄": "shijiazhuang city",
    "太原": "taiyuan city",
    "南宁": "nanning city",
    "海口": "haikou tropical",
    "珠海": "zhuhai city",
    "温州": "wenzhou city",
}


def get_db_session():
    """获取数据库会话"""
    if DB_TYPE == "mysql":
        url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    else:
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "xingzhi.db",
        )
        url = f"sqlite:///{db_path}"

    engine = create_engine(url, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


def fill_city_images(session: sessionmaker, fetcher: PixabayImageFetcher):
    """填充所有城市封面图"""
    logger.info("=" * 60)
    logger.info("开始填充城市封面图")
    logger.info("=" * 60)

    cities = session.query(City).filter(
        (City.cover_image == None) | (City.cover_image == "")
    ).all()
    total = len(cities)
    logger.info(f"待填充城市数: {total}")

    success = 0
    fail = 0

    for idx, city in enumerate(cities):
        city_name = city.name

        # 优先使用热门城市专属关键词
        keyword = CITY_KEYWORDS.get(city_name, f"{city_name} china city landscape")
        fallback = [f"{city_name} china", "china city"]

        logger.info(f"[{idx + 1}/{total}] {city_name}: '{keyword}'")

        image_url = fetcher.search_with_fallback(keyword, fallback)

        if image_url:
            city.cover_image = image_url
            session.commit()
            success += 1
            logger.info(f"  ✓ {image_url[:70]}...")
        else:
            fail += 1
            logger.warning(f"  ✗ 未找到")

    logger.info(f"城市图片填充完成: 成功 {success}, 失败 {fail}")
    return success, fail


def fill_top_scenic_spot_images(
    session: sessionmaker, fetcher: PixabayImageFetcher, top_n: int = 3
):
    """填充每个城市前N个景点图片"""
    logger.info("=" * 60)
    logger.info(f"开始填充景点图片（每个城市前{top_n}个）")
    logger.info("=" * 60)

    # 获取所有城市
    cities = session.query(City).all()
    total_cities = len(cities)
    logger.info(f"共 {total_cities} 个城市")

    total_success = 0
    total_fail = 0
    total_skipped = 0

    for idx, city in enumerate(cities):
        city_name = city.name

        # 获取该城市前N个没有图片的景点
        spots = session.query(ScenicSpot).filter(
            ScenicSpot.city_id == city.id,
            (ScenicSpot.image_url == None) | (ScenicSpot.image_url == ""),
        ).limit(top_n).all()

        if not spots:
            total_skipped += 1
            continue

        logger.info(f"\n[{idx + 1}/{total_cities}] {city_name}: {len(spots)} 个景点待填充")

        for spot in spots:
            spot_name = spot.name
            category = spot.category or ""

            # 搜索关键词
            keyword = f"{city_name} {spot_name}"
            fallback_queries = [
                f"{spot_name} china",
                f"{city_name} scenic spot",
                f"{category} china" if category else "china landscape",
                "china landmark scenery",
            ]

            logger.info(f"  {spot_name}: '{keyword}'")

            image_url = fetcher.search_with_fallback(keyword, fallback_queries)

            if image_url:
                spot.image_url = image_url
                session.commit()
                total_success += 1
                logger.info(f"    ✓ {image_url[:70]}...")
            else:
                total_fail += 1
                logger.warning(f"    ✗ 未找到")

    logger.info(f"\n景点图片填充完成: 成功 {total_success}, 失败 {total_fail}, 跳过 {total_skipped}")
    return total_success, total_fail


def main():
    parser = argparse.ArgumentParser(description="图片补充脚本（Pixabay）")
    parser.add_argument(
        "--table",
        type=str,
        choices=["cities", "spots", "all"],
        default="all",
        help="要填充的表 (默认: all)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="每个城市填充前N个景点 (默认: 3)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式：只填充前3个城市",
    )

    args = parser.parse_args()

    session = get_db_session()
    fetcher = PixabayImageFetcher()

    total_success = 0
    total_fail = 0

    try:
        if args.table in ("cities", "all"):
            if args.test:
                # 测试模式：只填充前3个城市
                logger.info("测试模式：只填充前3个城市")
                cities = session.query(City).filter(
                    (City.cover_image == None) | (City.cover_image == "")
                ).limit(3).all()

                for city in cities:
                    keyword = CITY_KEYWORDS.get(city.name, f"{city.name} china city")
                    logger.info(f"  {city.name}: '{keyword}'")
                    url = fetcher.search_with_fallback(keyword, [f"{city.name} china"])
                    if url:
                        city.cover_image = url
                        session.commit()
                        total_success += 1
                        logger.info(f"    ✓ {url[:70]}...")
                    else:
                        total_fail += 1
                        logger.warning(f"    ✗ 未找到")
            else:
                s, f = fill_city_images(session, fetcher)
                total_success += s
                total_fail += f

        if args.table in ("spots", "all"):
            if args.test:
                # 测试模式：只填充前2个城市的景点
                logger.info("测试模式：只填充前2个城市的景点")
                cities = session.query(City).limit(2).all()
                for city in cities:
                    spots = session.query(ScenicSpot).filter(
                        ScenicSpot.city_id == city.id,
                        (ScenicSpot.image_url == None) | (ScenicSpot.image_url == ""),
                    ).limit(2).all()

                    for spot in spots:
                        keyword = f"{city.name} {spot.name}"
                        logger.info(f"  {spot.name}: '{keyword}'")
                        url = fetcher.search_with_fallback(
                            keyword, [f"{spot.name} china", "china scenic spot"]
                        )
                        if url:
                            spot.image_url = url
                            session.commit()
                            total_success += 1
                            logger.info(f"    ✓ {url[:70]}...")
                        else:
                            total_fail += 1
                            logger.warning(f"    ✗ 未找到")
            else:
                s, f = fill_top_scenic_spot_images(session, fetcher, args.top)
                total_success += s
                total_fail += f

    finally:
        session.close()

    logger.info("=" * 60)
    logger.info(f"全部完成: 成功 {total_success}, 失败 {total_fail}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
