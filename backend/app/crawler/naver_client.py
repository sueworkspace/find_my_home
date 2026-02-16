"""
네이버 부동산 비공식 API HTTP 클라이언트

네이버 부동산 프론트엔드가 호출하는 내부 API를 역분석한 엔드포인트를 사용합니다.
비상업적 개인 사용 목적이며, rate limiting을 준수합니다.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

# 네이버 부동산 모바일 API (m.land.naver.com - 접근 가능 확인됨)
MOBILE_API_BASE = "https://m.land.naver.com"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "application/json",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://m.land.naver.com/",
}

# 재시도 설정
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # 지수 백오프 기본 초


class NaverLandClient:
    """네이버 부동산 비공식 API를 호출하는 HTTP 클라이언트.

    - httpx.AsyncClient 사용
    - 요청 간 딜레이(rate limiting) 준수
    - 에러 발생 시 지수 백오프 재시도
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._delay = settings.CRAWLER_DELAY_SECONDS

    async def _get_client(self) -> httpx.AsyncClient:
        """lazy-init으로 AsyncClient 생성."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=DEFAULT_HEADERS,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """클라이언트 종료."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(self, url: str, params: Optional[Dict] = None) -> Optional[Union[Dict[str, Any], List]]:
        """단일 GET 요청 (재시도 로직 포함).

        Args:
            url: 요청 URL
            params: 쿼리 파라미터

        Returns:
            JSON 응답 (dict 또는 list), 실패 시 None
        """
        client = await self._get_client()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug("요청 [%d/%d]: %s params=%s", attempt, MAX_RETRIES, url, params)
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    # Rate limit 초과 - 더 긴 대기
                    wait = RETRY_BACKOFF_BASE ** attempt * 2
                    logger.warning(
                        "Rate limited (429). %s초 후 재시도 (%d/%d)",
                        wait, attempt, MAX_RETRIES,
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code in (403, 401):
                    logger.error(
                        "접근 차단 (%d): %s - IP 차단 또는 헤더 변경 가능성",
                        response.status_code, url,
                    )
                    return None

                # 그 외 에러
                logger.warning(
                    "HTTP %d: %s (%d/%d)",
                    response.status_code, url, attempt, MAX_RETRIES,
                )

            except httpx.TimeoutException:
                logger.warning("타임아웃: %s (%d/%d)", url, attempt, MAX_RETRIES)
            except httpx.HTTPError as e:
                logger.warning("HTTP 에러: %s - %s (%d/%d)", url, str(e), attempt, MAX_RETRIES)

            # 지수 백오프 대기
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.info("%.1f초 후 재시도...", wait)
                await asyncio.sleep(wait)

        logger.error("최대 재시도 횟수 초과: %s", url)
        return None

    async def _throttle(self):
        """요청 간 딜레이 적용."""
        await asyncio.sleep(self._delay)

    # ──────────────────────────────────────────
    # 모바일 API 메서드 (m.land.naver.com)
    # ──────────────────────────────────────────

    async def get_cluster_list(
        self,
        cortar_no: str,
        lat: float,
        lon: float,
        z: int = 13,
    ) -> Optional[Dict]:
        """지역 내 아파트 단지 클러스터 목록 조회.

        GET https://m.land.naver.com/cluster/clusterList
        """
        delta = 0.03
        url = f"{MOBILE_API_BASE}/cluster/clusterList"
        params = {
            "view": "atcl",
            "cortarNo": cortar_no,
            "rletTpCd": "APT",
            "tradTpCd": "A1",
            "z": str(z),
            "lat": str(lat),
            "lon": str(lon),
            "btm": str(lat - delta),
            "lft": str(lon - delta),
            "top": str(lat + delta),
            "rgt": str(lon + delta),
            "addon": "COMPLEX",
            "isOnlyIs498": "false",
        }
        await self._throttle()
        return await self._request(url, params)

    async def get_article_list(
        self,
        cortar_no: str,
        lat: float,
        lon: float,
        z: int = 15,
        page: int = 1,
    ) -> Optional[Dict]:
        """지역 내 아파트 매매 매물 목록 조회 (최신순 20개).

        GET https://m.land.naver.com/cluster/ajax/articleList
        """
        delta = 0.01
        url = f"{MOBILE_API_BASE}/cluster/ajax/articleList"
        params = {
            "rletTpCd": "APT",
            "tradTpCd": "A1",
            "z": str(z),
            "lat": str(lat),
            "lon": str(lon),
            "btm": str(lat - delta),
            "lft": str(lon - delta),
            "top": str(lat + delta),
            "rgt": str(lon + delta),
            "cortarNo": cortar_no,
            "page": str(page),
        }
        await self._throttle()
        return await self._request(url, params)
