"""
Pixabay 图片搜索模块

通过 Pixabay API 搜索高质量免费图片。
免费API每小时5000次请求，限流宽松。
"""

import time
import logging
from typing import Optional, List

import requests

from config import PIXABAY_API_KEY, PIXABAY_API_URL

logger = logging.getLogger(__name__)


class PixabayImageFetcher:
    """Pixabay 图片搜索器"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or PIXABAY_API_KEY
        self._last_request_time = 0.0
        # 免费API每小时5000次，间隔约0.72秒
        self._min_interval = 0.8

    def _rate_limit(self):
        """请求频率控制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def search_images(self, query: str, num: int = 3) -> List[str]:
        """
        搜索图片，返回图片URL列表

        Args:
            query: 搜索关键词（英文效果更好）
            num: 需要返回的图片数量

        Returns:
            图片URL列表
        """
        if not query:
            return []

        self._rate_limit()

        params = {
            "key": self.api_key,
            "q": query,
            "image_type": "photo",
            "orientation": "horizontal",
            "per_page": max(3, min(num, 20)),  # Pixabay要求per_page范围3-200
            "lang": "zh",
            "safesearch": True,
        }

        try:
            response = requests.get(
                PIXABAY_API_URL,
                params=params,
                timeout=10,
            )

            if response.status_code != 200:
                logger.warning(f"Pixabay API 返回 {response.status_code}: {response.text[:100]}")
                return []

            data = response.json()
            hits = data.get("hits", [])

            if not hits:
                return []

            urls = []
            for hit in hits[:num]:
                # 优先取大图，其次取中图
                url = hit.get("largeImageURL") or hit.get("webformatURL") or ""
                if url:
                    urls.append(url)

            return urls

        except requests.exceptions.RequestException as e:
            logger.warning(f"Pixabay 请求失败: {e}")
            return []

    def search_image(self, query: str) -> Optional[str]:
        """
        搜索图片并返回第一张的URL

        Args:
            query: 搜索关键词

        Returns:
            图片URL 或 None
        """
        urls = self.search_images(query, num=1)
        return urls[0] if urls else None

    def search_with_fallback(
        self, primary_query: str, fallback_queries: list = None
    ) -> Optional[str]:
        """
        搜索图片，带备用关键词

        Args:
            primary_query: 主搜索关键词
            fallback_queries: 备用关键词列表

        Returns:
            图片URL 或 None
        """
        queries = [primary_query]
        if fallback_queries:
            queries.extend(fallback_queries)

        for query in queries:
            logger.debug(f"  搜索图片: '{query}'")
            url = self.search_image(query)
            if url:
                return url

        return None
