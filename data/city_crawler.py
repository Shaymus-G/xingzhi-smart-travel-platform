"""
城市数据爬取模块

从高德地图API获取城市列表，并过滤出目标城市的数据。
"""

import logging
from typing import List, Optional

from amap_client import AMapClient
from config import USE_ALL_CITIES, TARGET_CITIES

logger = logging.getLogger(__name__)


class CityCrawler:
    """城市数据爬取器"""

    def __init__(self, client: Optional[AMapClient] = None):
        self.client = client or AMapClient()

    def get_all_cities(self) -> list:
        """
        获取高德地图API中的所有城市列表

        Returns:
            所有城市列表
        """
        logger.info("正在获取全国城市列表...")
        cities = self.client.get_city_list()
        logger.info(f"获取到 {len(cities)} 个城市")
        return cities

    def get_target_cities(self, target_names: List[str] = None) -> list:
        """
        获取城市列表

        策略：
        - 如果显式传入了 target_names，则只返回匹配的城市
        - 如果 USE_ALL_CITIES=True，则返回所有城市
        - 否则使用 config.py 中的 TARGET_CITIES 列表

        Args:
            target_names: 目标城市名称列表（可选）

        Returns:
            城市列表
        """
        all_cities = self.get_all_cities()

        # 如果显式传入了城市名，按指定城市过滤
        if target_names is not None:
            matched = []
            for city in all_cities:
                if city["name"] in target_names:
                    matched.append(city)

            # 按输入顺序排序
            city_order = {name: idx for idx, name in enumerate(target_names)}
            matched.sort(key=lambda c: city_order.get(c["name"], 999))

            # 输出未匹配到的目标城市
            matched_names = {c["name"] for c in matched}
            for name in target_names:
                if name not in matched_names:
                    logger.warning(f"目标城市 '{name}' 未在API返回中找到")

            logger.info(f"匹配到 {len(matched)}/{len(target_names)} 个指定城市")
            return matched

        # 未传入城市名时，按 USE_ALL_CITIES 配置决定
        if USE_ALL_CITIES:
            logger.info(f"使用全部城市模式: 共 {len(all_cities)} 个城市")
            return all_cities

        # 回退到配置文件中的 TARGET_CITIES
        targets = TARGET_CITIES
        matched = [c for c in all_cities if c["name"] in targets]
        matched.sort(key=lambda c: targets.index(c["name"]) if c["name"] in targets else 999)
        logger.info(f"匹配到 {len(matched)}/{len(targets)} 个目标城市")
        return matched

    def get_city_by_name(self, city_name: str) -> Optional[dict]:
        """
        根据城市名称查找城市信息

        Args:
            city_name: 城市名称

        Returns:
            城市信息字典，未找到返回 None
        """
        cities = self.get_all_cities()
        for city in cities:
            if city["name"] == city_name:
                return city
        return None