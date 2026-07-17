"""
数据清洗与转换模块

将高德地图API返回的POI数据字段映射到数据库Schema字段。
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清洗器"""

    @staticmethod
    def extract_location(location_str: str) -> tuple:
        """
        从高德地图的 location 字段中提取经纬度

        Args:
            location_str: "116.397428,39.90923" 格式的字符串

        Returns:
            (lng, lat) 元组
        """
        if not location_str or "," not in location_str:
            return "", ""
        parts = location_str.split(",")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
        return "", ""

    @staticmethod
    def safe_float(value) -> Optional[float]:
        """
        安全地将字符串转为浮点数

        Args:
            value: 输入值，可能是字符串、数字或 None

        Returns:
            浮点数或 None
        """
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def extract_category(type_str: str) -> str:
        """
        从高德POI的type字段中提取一级分类

        高德type格式: "餐饮服务;中餐厅;川菜馆"
        提取: "餐饮服务"

        Args:
            type_str: 高德API的type字段

        Returns:
            一级分类名称
        """
        if not type_str:
            return ""
        return type_str.split(";")[0].strip()

    @staticmethod
    def extract_image_url(photos: list) -> str:
        """
        从高德POI的photos字段中提取第一张图片URL

        Args:
            photos: photos 列表，格式为 [{"url": "...", "title": "..."}]

        Returns:
            图片URL或空字符串
        """
        if not photos or not isinstance(photos, list):
            return ""
        for photo in photos:
            url = photo.get("url", "")
            if url:
                return url
        return ""

    @staticmethod
    def parse_open_time(time_str: Optional[str]) -> str:
        """
        解析开放时间

        Args:
            time_str: 高德API返回的开放时间信息

        Returns:
            清洗后的开放时间字符串
        """
        if not time_str:
            return ""
        # 移除多余的空格和换行
        return re.sub(r"\s+", " ", time_str).strip()

    def clean_city(self, raw_city: dict) -> dict:
        """
        清洗城市数据

        Args:
            raw_city: 高德API返回的城市数据

        Returns:
            符合 cities 表结构的字典
        """
        return {
            "name": raw_city.get("name", ""),
            "province": raw_city.get("province", ""),
            "country": "中国",
            "description": "",
            "cover_image": "",
            "latitude": raw_city.get("lat", ""),
            "longitude": raw_city.get("lng", ""),
        }

    def clean_scenic_spot(self, raw_poi: dict, city_id: int) -> dict:
        """
        清洗景点POI数据

        Args:
            raw_poi: 高德API返回的POI数据
            city_id: 对应的城市ID

        Returns:
            符合 scenic_spots 表结构的字典
        """
        lng, lat = self.extract_location(raw_poi.get("location", ""))

        return {
            "city_id": city_id,
            "name": raw_poi.get("name", ""),
            "description": raw_poi.get("adname", ""),
            "address": raw_poi.get("address", ""),
            "category": self.extract_category(raw_poi.get("type", "")),
            "score": self.safe_float(raw_poi.get("rating")),
            "price": self.safe_float(raw_poi.get("cost")),
            "open_time": self.parse_open_time(raw_poi.get("opentime", "")),
            "latitude": lat,
            "longitude": lng,
            "image_url": self.extract_image_url(raw_poi.get("photos", [])),
        }

    def clean_hotel(self, raw_poi: dict, city_id: int) -> dict:
        """
        清洗酒店POI数据

        Args:
            raw_poi: 高德API返回的POI数据
            city_id: 对应的城市ID

        Returns:
            符合 hotels 表结构的字典
        """
        lng, lat = self.extract_location(raw_poi.get("location", ""))

        return {
            "city_id": city_id,
            "name": raw_poi.get("name", ""),
            "description": raw_poi.get("adname", ""),
            "address": raw_poi.get("address", ""),
            "price": self.safe_float(raw_poi.get("cost")),
            "score": self.safe_float(raw_poi.get("rating")),
            "open_time": self.parse_open_time(raw_poi.get("opentime", "")),
            "latitude": lat,
            "longitude": lng,
            "image_url": self.extract_image_url(raw_poi.get("photos", [])),
        }

    def clean_restaurant(self, raw_poi: dict, city_id: int) -> dict:
        """
        清洗餐饮POI数据

        Args:
            raw_poi: 高德API返回的POI数据
            city_id: 对应的城市ID

        Returns:
            符合 restaurants 表结构的字典
        """
        lng, lat = self.extract_location(raw_poi.get("location", ""))

        return {
            "city_id": city_id,
            "name": raw_poi.get("name", ""),
            "type": self.extract_category(raw_poi.get("type", "")),
            "description": raw_poi.get("adname", ""),
            "price_level": self.safe_float(raw_poi.get("cost")),
            "score": self.safe_float(raw_poi.get("rating")),
            "address": raw_poi.get("address", ""),
            "latitude": lat,
            "longitude": lng,
            "image_url": self.extract_image_url(raw_poi.get("photos", [])),
        }

    def clean_poi_list(self, raw_pois: list, table_name: str,
                       city_id: int) -> list:
        """
        清洗一批POI数据

        Args:
            raw_pois: 原始POI数据列表
            table_name: 目标表名 (scenic_spots / hotels / restaurants)
            city_id: 城市ID

        Returns:
            清洗后的数据字典列表
        """
        clean_methods = {
            "scenic_spots": self.clean_scenic_spot,
            "hotels": self.clean_hotel,
            "restaurants": self.clean_restaurant,
        }

        clean_method = clean_methods.get(table_name)
        if not clean_method:
            logger.warning(f"未知的POI表类型: {table_name}")
            return []

        cleaned = []
        for poi in raw_pois:
            try:
                cleaned_item = clean_method(poi, city_id)
                cleaned.append(cleaned_item)
            except Exception as e:
                logger.warning(f"清洗数据时出错: {e}, 数据: {poi.get('name', '')}")
                continue

        logger.info(f"清洗完成: {table_name} {len(cleaned)}/{len(raw_pois)} 条有效数据")
        return cleaned