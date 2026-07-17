"""
高德地图 API 客户端

封装对高德地图 Web服务 API 的 HTTP 请求，提供：
- 统一的请求方法
- 自动重试机制
- 请求频率控制
- 错误处理与日志
"""

import time
import logging
from typing import Optional

import requests

from config import AMAP_API_KEY, REQUEST_INTERVAL, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)


class AMapClient:
    """高德地图API客户端"""

    # 高德地图API基础URL
    DISTRICT_URL = "https://restapi.amap.com/v3/config/district"
    PLACE_TEXT_URL = "https://restapi.amap.com/v3/place/text"
    PLACE_AROUND_URL = "https://restapi.amap.com/v3/place/around"
    GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or AMAP_API_KEY
        self._last_request_time = 0.0

    def _rate_limit(self):
        """请求频率控制：确保每次请求间隔至少 REQUEST_INTERVAL 秒"""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _request(self, url: str, params: dict) -> Optional[dict]:
        """
        发送HTTP请求，带重试机制

        Args:
            url: API地址
            params: 请求参数

        Returns:
            解析后的JSON响应字典，失败返回 None
        """
        params["key"] = self.api_key

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._rate_limit()
                response = requests.get(url, params=params, timeout=10)
                data = response.json()

                if data.get("status") != "1":
                    error_info = data.get("info", "未知错误")
                    error_code = data.get("infocode", "")
                    logger.warning(
                        f"API返回错误 [第{attempt}次尝试]: "
                        f"code={error_code}, info={error_info}"
                    )

                    # 如果是Key问题，不需要重试
                    if error_code in ("10001", "10003", "20001"):
                        logger.error(f"API Key错误或权限不足，终止请求: {error_info}")
                        return None

                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY * attempt)
                        continue
                    return None

                return data

            except requests.exceptions.Timeout as e:
                logger.warning(
                    f"请求超时 [第{attempt}次尝试]: {url}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    logger.error(f"请求超时，已达最大重试次数: {url}")
                    return None

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"请求异常 [第{attempt}次尝试]: {e}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    logger.error(f"请求失败，已达最大重试次数: {e}")
                    return None

            except Exception as e:
                logger.error(f"未知错误: {e}")
                return None

        return None

    def get_city_list(self, country: str = "中国") -> list:
        """
        获取全国城市列表

        通过行政区域查询接口，获取中国所有省份及下辖城市。

        Args:
            country: 国家名称，默认"中国"

        Returns:
            城市列表，每个元素为 dict:
            {
                "name": "北京市",
                "adcode": "110000",
                "province": "北京市",
                "lat": "39.9042",
                "lng": "116.4074"
            }
        """
        params = {
            "keywords": country,
            "subdistrict": 3,  # 获取省市区三级
        }

        data = self._request(self.DISTRICT_URL, params)
        if not data:
            return []

        cities = []
        provinces = data.get("districts", [{}])[0].get("districts", [])

        for province in provinces:
            province_name = province.get("name", "")
            province_level = province.get("level", "")

            if province_level == "直辖市":
                # 直辖市：城市名就是直辖市本身
                cities.append({
                    "name": province_name.replace("市", ""),
                    "adcode": province.get("adcode", ""),
                    "province": province_name,
                    "lat": self._extract_center_lat(province),
                    "lng": self._extract_center_lng(province),
                })
                continue

            # 普通省份：遍历其下辖城市
            for city in province.get("districts", []):
                city_name = city.get("name", "")
                # 跳过"省直辖县级行政区划"等特殊条目
                if city_name in ("省直辖县级行政区划", "自治区直辖县级行政区划"):
                    continue

                cities.append({
                    "name": city_name.replace("市", ""),
                    "adcode": city.get("adcode", ""),
                    "province": province_name,
                    "lat": self._extract_center_lat(city),
                    "lng": self._extract_center_lng(city),
                })

        return cities

    def search_poi(self, city_adcode: str, keywords: str,
                   page: int = 1, page_size: int = 25) -> Optional[dict]:
        """
        搜索POI数据（文本搜索）

        根据城市adcode和关键词，搜索兴趣点（POI）数据。

        Args:
            city_adcode: 城市adcode
            keywords: 搜索关键词，如"景点"、"酒店"、"餐饮服务"
            page: 页码，从1开始
            page_size: 每页条数，最大25

        Returns:
            API响应字典，包含pois列表等信息
        """
        params = {
            "keywords": keywords,
            "city": city_adcode,
            "offset": page_size,
            "page": page,
            "extensions": "all",  # 获取详细信息
        }

        return self._request(self.PLACE_TEXT_URL, params)

    def search_poi_by_region(self, city_adcode: str, keywords: str,
                             max_pages: int = 10) -> list:
        """
        搜索指定城市指定关键词的所有POI数据（自动分页）

        Args:
            city_adcode: 城市adcode
            keywords: 搜索关键词
            max_pages: 最大爬取页数

        Returns:
            POI数据列表
        """
        all_pois = []

        for page in range(1, max_pages + 1):
            result = self.search_poi(city_adcode, keywords, page)
            if not result or result.get("status") != "1":
                break

            pois = result.get("pois", [])
            if not pois:
                break

            all_pois.extend(pois)
            logger.debug(f"  第{page}页: 获取到{len(pois)}条POI")

            # 判断是否最后一页
            count = int(result.get("count", 0))
            if len(all_pois) >= count:
                break

        return all_pois

    def geocode(self, address: str, city: str = "") -> Optional[dict]:
        """
        地理编码：将地址解析为经纬度

        Args:
            address: 地址描述
            city: 所在城市

        Returns:
            地理编码结果
        """
        params = {
            "address": address,
            "city": city,
        }
        return self._request(self.GEOCODE_URL, params)

    @staticmethod
    def _extract_center_lat(district: dict) -> str:
        """从行政区数据中提取中心点纬度"""
        center = district.get("center", "")
        if center and "," in center:
            return center.split(",")[1]
        return ""

    @staticmethod
    def _extract_center_lng(district: dict) -> str:
        """从行政区数据中提取中心点经度"""
        center = district.get("center", "")
        if center and "," in center:
            return center.split(",")[0]
        return ""