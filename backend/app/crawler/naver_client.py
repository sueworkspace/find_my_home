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
        self.api_call_count: int = 0  # 배치 쿨다운용 API 호출 카운터

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

                self.api_call_count += 1  # 모든 요청 카운트 (차단 감지용)
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

    # ──────────────────────────────────────────
    # 지역/단지/매물 조회 메서드 (크롤러에서 사용)
    # ──────────────────────────────────────────

    async def get_sub_regions(self, cortar_no: str) -> Optional[List[Dict]]:
        """하위 지역 목록 조회.

        시/도 코드 → 시/군/구 목록, 시/군/구 코드 → 읍/면/동 목록을 반환.

        API 응답: {"result": {"list": [{"CortarNo": "...", "CortarNm": "..."}, ...]}}
        → 정규화하여 [{"cortarNo": "...", "cortarName": "..."}, ...] 리스트로 반환

        Args:
            cortar_no: 상위 지역 코드 (cortarNo)

        Returns:
            지역 dict 리스트 (정규화된 키), 실패 시 None
        """
        url = f"{MOBILE_API_BASE}/map/getRegionList"
        params = {"cortarNo": cortar_no}
        await self._throttle()
        raw = await self._request(url, params)
        if not raw:
            return None

        # 응답 정규화: {"result": {"list": [...]}} → 리스트
        items = []
        result = raw.get("result")
        if isinstance(result, dict):
            items = result.get("list", [])
        elif isinstance(result, list):
            items = result

        # PascalCase → 소문자 키 정규화
        normalized = []
        for item in items:
            normalized.append({
                "cortarNo": item.get("CortarNo", ""),
                "cortarName": item.get("CortarNm", ""),
                "lat": item.get("CenterLat"),
                "lon": item.get("CenterLon"),
            })
        return normalized

    async def get_complex_list_in_region(
        self,
        cortar_no: str,
        page: int = 1,
    ) -> Optional[Dict]:
        """지역 내 아파트 단지 목록 조회.

        API 응답: {"result": [{"hscpNo": "881", "hscpNm": "개포더샵트리에", ...}, ...]}
        → 정규화하여 {"complexList": [...], "totalCount": N} 형태로 반환

        Args:
            cortar_no: 동 코드 (cortarNo)
            page: 페이지 번호

        Returns:
            {"complexList": [...], "totalCount": N} 형태의 dict, 실패 시 None
        """
        url = f"{MOBILE_API_BASE}/complex/ajax/complexListByCortarNo"
        params = {
            "cortarNo": cortar_no,
            "order": "rank",
            "realEstateType": "APT",
            "tradeType": "A1",
            "page": str(page),
        }
        await self._throttle()
        raw = await self._request(url, params)
        if not raw:
            return None

        # 응답 정규화: {"result": [...]} → {"complexList": [...], "totalCount": N}
        items = raw.get("result", [])
        if not isinstance(items, list):
            items = []

        # hscpNo/hscpNm → complexNo/complexName 키 정규화
        complexes = []
        for item in items:
            complexes.append({
                "complexNo": item.get("hscpNo", ""),
                "complexName": item.get("hscpNm", ""),
                "dealCnt": item.get("dealCnt", 0),
                "totalHouseholdCount": item.get("totHsehCnt"),
                "useApproveYmd": item.get("useAprvYmd"),
                "latitude": item.get("lat"),
                "longitude": item.get("lon"),
                "cortarAddress": item.get("cortarAddress", ""),
                "address": item.get("dtlAddress", ""),
            })

        return {"complexList": complexes, "totalCount": len(complexes)}

    async def get_articles_for_complex(
        self,
        complex_no: str,
        trade_type: str = "A1",
        page: int = 1,
    ) -> Optional[Dict]:
        """특정 단지의 매매 매물 목록 조회.

        API 응답: {"result": {"list": [{"atclNo": "...", "atclNm": "...", ...}], "totalCount": N}}
        → 정규화하여 {"articleList": [...], "totalCount": N} 형태로 반환

        Args:
            complex_no: 네이버 단지 번호 (hscpNo)
            trade_type: 거래 유형 (A1=매매, B1=전세, B2=월세)
            page: 페이지 번호

        Returns:
            {"articleList": [...], "totalCount": N} 형태의 dict, 실패 시 None
        """
        url = f"{MOBILE_API_BASE}/complex/getComplexArticleList"
        params = {
            "hscpNo": complex_no,
            "tradTpCd": trade_type,
            "order": "prc",
            "showR0": "N",
            "page": str(page),
        }
        await self._throttle()
        raw = await self._request(url, params)
        if not raw:
            return None

        # 응답 정규화: {"result": {"list": [...], "totalCount": N}}
        result = raw.get("result", {})
        if not isinstance(result, dict):
            return {"articleList": [], "totalCount": 0}

        items = result.get("list", [])
        total_count = result.get("totalCount", len(items))

        # 매물 키 정규화
        articles = []
        for item in items:
            # flrInfo: "저/16" → "저" 또는 "15/16" 형태
            articles.append({
                "articleNo": item.get("atclNo", ""),
                "articleName": item.get("atclNm", ""),
                "dealOrWarrantPrc": item.get("prcInfo", ""),
                "area1": item.get("spc1"),  # 공급면적
                "area2": item.get("spc2"),  # 전용면적
                "floorInfo": item.get("flrInfo", ""),
                "buildingName": item.get("bildNm", ""),
                "articleConfirmYmd": item.get("cfmYmd", ""),
                "direction": item.get("direction", ""),
            })

        return {"articleList": articles, "totalCount": total_count}
