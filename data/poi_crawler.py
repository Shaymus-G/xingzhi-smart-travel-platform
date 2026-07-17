"""
POI数据爬取模块

根据城市列表和POI类型，爬取景点、酒店、餐饮等数据。
"""

import logging
from typing import List, Optional

from amap_client import AMapClient
from config import POI_TYPES, PAGE_SIZE, MAX_PAGES

logger = logging.getLogger(__name__)


class PoiCrawler:
    """POI数据爬取器"""

    def __init__(self, client: Optional[AMapClient] = None):
        self.client = client or AMapClient()

    def crawl_city_pois(self, city: dict, poi_types: dict = None) -> dict:
        """
        爬取单个城市的所有POI数据

        Args:
            city: 城市信息字典，包含 name, adcode 等字段
            poi_types: POI类型配置，默认使用 config.py 中的配置

        Returns:
            {
                "scenic_spots": [...],
                "hotels": [...],
                "restaurants": [...]
            }
        """
        types = poi_types or POI_TYPES
        city_name = city.get("name", "")
        city_adcode = city.get("adcode", "")

        logger.info(f"===== 开始爬取 [{city_name}] 的POI数据 =====")

        result = {}
        for keyword, table_name in types.items():
            logger.info(f"  正在爬取 {city_name} 的 [{keyword}] 数据...")
            pois = self.client.search_poi_by_region(
                city_adcode, keyword, max_pages=MAX_PAGES
            )
            logger.info(f"  完成: {city_name} - {keyword}, 共 {len(pois)} 条")
            result[table_name] = pois

        return result

    def crawl_all_cities(self, cities: list, poi_types: dict = None) -> dict:
        """
        爬取多个城市的所有POI数据

        Args:
            cities: 城市列表
            poi_types: POI类型配置

        Returns:
            {
                "scenic_spots": [...],
                "hotels": [...],
                "restaurants": [...]
            }
        """
        types = poi_types or POI_TYPES

        # 按表名汇总所有城市的数据
        aggregated = {table_name: [] for table_name in types.values()}

        for idx, city in enumerate(cities):
            city_name = city.get("name", "")
            logger.info(
                f"\n===== 正在处理 [{idx + 1}/{len(cities)}] {city_name} ====="
            )

            city_result = self.crawl_city_pois(city, types)

            for table_name, pois in city_result.items():
                # 为每条POI数据标注所属城市信息
                for poi in pois:
                    poi["_city_name"] = city_name
                    poi["_city_adcode"] = city.get("adcode", "")
                aggregated[table_name].extend(pois)

        # 汇总统计
        for table_name, pois in aggregated.items():
            logger.info(
                f"汇总: {table_name} 共 {len(pois)} 条数据"
            )

        return aggregated