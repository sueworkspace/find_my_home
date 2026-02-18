"""
KB부동산(kbland.kr) 내부 API를 이용한 KB시세 조회 클라이언트

kbland.kr 프론트엔드가 호출하는 api.kbland.kr 내부 API를 역분석한 엔드포인트를 사용합니다.
비상업적 개인 사용 목적이며, rate limiting을 준수합니다.

주요 기능:
- 법정동코드로 해당 지역 아파트 단지 목록 조회
- 단지별 면적 타입 정보 조회
- 면적별 KB시세(일반거래가, 상한가, 하한가) 조회
- 네이버 부동산 단지와 KB 단지 매칭
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# KB부동산 API 베이스 URL
# kbland.kr 프론트엔드에서 사용하는 내부 API 서버
# ──────────────────────────────────────────
KB_API_BASE = "https://api.kbland.kr"

# KB부동산 내부 API 엔드포인트
# 지역별 단지 목록 (법정동코드 기반)
COMPLEX_LIST_URL = f"{KB_API_BASE}/land-price/price/fastPriceComplexName"
# 단지 간략 정보 (시세 범위 포함)
COMPLEX_BRIF_URL = f"{KB_API_BASE}/land-complex/complex/brif"
# 단지 면적별 타입 정보
COMPLEX_TYPE_URL = f"{KB_API_BASE}/land-complex/complex/typInfo"
# 면적별 KB시세 상세 조회
PRICE_INFO_URL = f"{KB_API_BASE}/land-price/price/BasePrcInfoNew"

# kbland.kr 프론트엔드 Origin / Referer (CORS 및 접근 제어용)
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://kbland.kr",
    "Referer": "https://kbland.kr/",
}

# 재시도 설정
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # 지수 백오프 기본 초

# KB 시세 딜레이 (rate limiting)
KB_DELAY_SECONDS = 1.5

# ──────────────────────────────────────────
# 서울 주요 구 법정동코드 매핑 (kbland.kr용)
# 구-level 코드 (fallback용)
# ──────────────────────────────────────────
LAWDCD_MAP: Dict[str, Dict[str, str]] = {
    "서울특별시": {
        "강남구": "1168000000",
        "서초구": "1165000000",
        "송파구": "1171000000",
        "강동구": "1174000000",
        "마포구": "1144000000",
        "용산구": "1117000000",
        "성동구": "1120000000",
        "광진구": "1121500000",
        "영등포구": "1156000000",
        "동작구": "1159000000",
    },
}

# ──────────────────────────────────────────
# 동-level 법정동코드 매핑
# KB API(fastPriceComplexName)는 동-level 코드가 필요함
# ──────────────────────────────────────────
DONG_LAWDCD_MAP: Dict[str, Dict[str, Dict[str, str]]] = {
    "서울특별시": {
        "강남구": {
            "역삼동": "1168010100",
            "개포동": "1168010300",
            "청담동": "1168010400",
            "삼성동": "1168010500",
            "대치동": "1168010600",
            "신사동": "1168010700",
            "논현동": "1168010800",
            "압구정동": "1168011000",
            "세곡동": "1168011100",
            "자곡동": "1168011200",
            "율현동": "1168011300",
            "일원동": "1168011400",
            "수서동": "1168011500",
            "도곡동": "1168011800",
        },
        "서초구": {
            "방배동": "1165010100",
            "양재동": "1165010200",
            "우면동": "1165010300",
            "잠원동": "1165010600",
            "반포동": "1165010700",
            "서초동": "1165010800",
            "내곡동": "1165010900",
            "신원동": "1165011100",
        },
        "송파구": {
            "잠실동": "1171010100",
            "신천동": "1171010200",
            "풍납동": "1171010300",
            "송파동": "1171010400",
            "석촌동": "1171010500",
            "삼전동": "1171010600",
            "가락동": "1171010700",
            "문정동": "1171010800",
            "장지동": "1171010900",
            "방이동": "1171011100",
            "오금동": "1171011200",
            "거여동": "1171011300",
            "마천동": "1171011400",
        },
    },
}


def get_lawdcd(
    sido: str,
    sigungu: str,
    dong: Optional[str] = None,
) -> Optional[str]:
    """법정동코드를 조회한다.

    dong이 있으면 동-level 코드 반환 (KB API 호환),
    없으면 구-level 코드 반환 (fallback).

    Args:
        sido: 시/도 (예: "서울특별시")
        sigungu: 시/군/구 (예: "강남구")
        dong: 동 이름 (예: "대치동", 선택)

    Returns:
        10자리 법정동코드 문자열, 없으면 None
    """
    if dong:
        dong_map = DONG_LAWDCD_MAP.get(sido, {}).get(sigungu, {})
        code = dong_map.get(dong)
        if code:
            return code
    # fallback: 구-level 코드
    return LAWDCD_MAP.get(sido, {}).get(sigungu)


class KBPriceClient:
    """KB부동산 내부 API를 호출하는 HTTP 클라이언트.

    - httpx.AsyncClient 사용 (비동기 HTTP 요청)
    - 요청 간 딜레이(rate limiting) 준수
    - 에러 발생 시 지수 백오프 재시도
    - kbland.kr 프론트엔드 요청을 모사하는 헤더 설정
    """

    def __init__(self, delay: Optional[float] = None):
        """
        Args:
            delay: 요청 간 딜레이(초). None이면 기본값(KB_DELAY_SECONDS) 사용
        """
        self._client: Optional[httpx.AsyncClient] = None
        self._delay = delay if delay is not None else KB_DELAY_SECONDS

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
        """클라이언트 리소스 정리."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _throttle(self):
        """요청 간 딜레이 적용 (rate limiting)."""
        await asyncio.sleep(self._delay)

    async def _request(
        self,
        url: str,
        params: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """HTTP GET 요청 실행 (재시도 로직 포함).

        Args:
            url: 요청 URL
            params: 쿼리 파라미터

        Returns:
            JSON 응답의 dataBody, 실패 시 None
        """
        client = await self._get_client()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    header = data.get("dataHeader", {})
                    # resultCode "10000" = 정상
                    if header.get("resultCode") == "10000":
                        return data.get("dataBody")
                    else:
                        logger.warning(
                            "KB API 비정상 응답: %s (code=%s)",
                            header.get("message", "?"),
                            header.get("resultCode", "?"),
                        )
                        return data.get("dataBody")

                if response.status_code == 429:
                    wait = RETRY_BACKOFF_BASE ** attempt * 2
                    logger.warning(
                        "KB API Rate limited. %.1f초 후 재시도 (%d/%d)",
                        wait, attempt, MAX_RETRIES,
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code in (403, 401):
                    logger.error(
                        "KB API 접근 차단 (%d): 헤더 또는 IP 차단 가능성",
                        response.status_code,
                    )
                    return None

                logger.warning(
                    "KB API HTTP %d (%d/%d)",
                    response.status_code, attempt, MAX_RETRIES,
                )

            except httpx.TimeoutException:
                logger.warning("KB API 타임아웃 (%d/%d)", attempt, MAX_RETRIES)
            except httpx.HTTPError as e:
                logger.warning("KB API 에러: %s (%d/%d)", str(e), attempt, MAX_RETRIES)

            # 지수 백오프 대기
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                await asyncio.sleep(wait)

        logger.error("KB API 최대 재시도 횟수 초과: %s", url)
        return None

    # ──────────────────────────────────────────
    # 지역별 단지 목록 조회
    # ──────────────────────────────────────────

    async def get_complex_list(
        self,
        lawdcd: str,
    ) -> List[Dict[str, Any]]:
        """법정동코드로 해당 지역의 아파트 단지 목록을 조회한다.

        Args:
            lawdcd: 법정동코드 (10자리, 예: "1168010600" = 대치동)

        Returns:
            단지 목록 리스트 (단지기본일련번호, 단지명, 주소 등 포함)
        """
        await self._throttle()
        body = await self._request(COMPLEX_LIST_URL, params={"법정동코드": lawdcd})

        if body and isinstance(body, dict):
            return body.get("data", [])
        return []

    # ──────────────────────────────────────────
    # 단지 간략 정보 조회 (시세 범위 포함)
    # ──────────────────────────────────────────

    async def get_complex_brif(
        self,
        complex_id: int,
    ) -> Optional[Dict[str, Any]]:
        """KB 단지번호로 단지 간략 정보를 조회한다.

        최소/최대 매매일반거래가 등 시세 범위 정보가 포함되어 있다.

        Args:
            complex_id: KB 단지기본일련번호

        Returns:
            단지 간략 정보 dict, 실패 시 None
        """
        await self._throttle()
        body = await self._request(
            COMPLEX_BRIF_URL,
            params={"단지기본일련번호": str(complex_id), "매물종별구분": "01"},
        )

        if body and isinstance(body, dict):
            return body.get("data")
        return None

    # ──────────────────────────────────────────
    # 단지 면적별 타입 정보 조회
    # ──────────────────────────────────────────

    async def get_complex_types(
        self,
        complex_id: int,
    ) -> List[Dict[str, Any]]:
        """KB 단지번호로 면적별 타입 정보를 조회한다.

        면적일련번호, 전용면적, 공급면적 등을 반환한다.
        이 면적일련번호가 KB시세 조회에 필요하다.

        Args:
            complex_id: KB 단지기본일련번호

        Returns:
            면적 타입 리스트
        """
        await self._throttle()
        body = await self._request(
            COMPLEX_TYPE_URL,
            params={"단지기본일련번호": str(complex_id), "매물종별구분": "01"},
        )

        if body and isinstance(body, dict):
            return body.get("data", [])
        return []

    # ──────────────────────────────────────────
    # 면적별 KB시세 상세 조회
    # ──────────────────────────────────────────

    async def get_price_by_area(
        self,
        complex_id: int,
        area_seq: int,
    ) -> Optional[Dict[str, Any]]:
        """KB 단지번호 + 면적일련번호로 상세 KB시세를 조회한다.

        매매일반거래가, 매매상한가, 매매하한가 등을 반환한다.

        Args:
            complex_id: KB 단지기본일련번호
            area_seq: 면적일련번호 (typInfo에서 가져온 값)

        Returns:
            시세 정보 dict, 실패 시 None
        """
        await self._throttle()
        body = await self._request(
            PRICE_INFO_URL,
            params={
                "단지기본일련번호": str(complex_id),
                "면적일련번호": str(area_seq),
                "매물종별구분": "01",
            },
        )

        if body and isinstance(body, dict):
            data = body.get("data", {})
            # 시세 배열에서 첫번째 항목 추출
            sise_list = data.get("시세", [])
            if sise_list:
                return sise_list[0]
        return None

    # ──────────────────────────────────────────
    # 단지의 전체 면적별 KB시세 조회 (통합)
    # ──────────────────────────────────────────

    async def get_all_prices(
        self,
        complex_id: int,
    ) -> List[Dict[str, Any]]:
        """KB 단지번호로 모든 면적의 KB시세를 한번에 조회한다.

        1) 면적 타입 목록 조회
        2) 매매건수가 있는 면적별로 시세 조회
        3) 정규화된 시세 리스트 반환

        Args:
            complex_id: KB 단지기본일련번호

        Returns:
            면적별 KB시세 리스트 [{area_sqm, price_lower, price_mid, price_upper}, ...]
        """
        # 1단계: 면적 타입 조회
        types = await self.get_complex_types(complex_id)
        if not types:
            logger.warning("KB 면적 타입 조회 실패: complex_id=%d", complex_id)
            return []

        results = []
        # 이미 조회한 면적 중복 방지 (동일 면적이 여러 타입으로 존재)
        seen_areas = set()

        for typ in types:
            area_seq = typ.get("면적일련번호")
            area_sqm_str = typ.get("전용면적", "")
            if not area_seq or not area_sqm_str:
                continue

            try:
                area_sqm = float(area_sqm_str)
            except (ValueError, TypeError):
                continue

            # 동일 면적 중복 스킵 (소수점 1자리로 반올림하여 비교)
            area_key = round(area_sqm, 1)
            if area_key in seen_areas:
                continue

            # 2단계: 면적별 시세 조회
            price_data = await self.get_price_by_area(complex_id, area_seq)
            if not price_data:
                continue

            # 3단계: 시세 파싱
            price_mid = price_data.get("매매일반거래가")
            price_upper = price_data.get("매매상한가")

            # 하한가 필드가 여러 이름으로 존재할 수 있음
            price_lower = price_data.get("매매하한가") or price_data.get("매매하한거래가")

            # 최소한 일반거래가가 있어야 유효
            if price_mid is None:
                continue

            seen_areas.add(area_key)
            results.append({
                "area_sqm": area_sqm,
                "price_lower": price_lower,
                "price_mid": price_mid,
                "price_upper": price_upper,
            })

            logger.info(
                "KB시세: %d | %.1f㎡ | 일반=%s 상한=%s 하한=%s",
                complex_id, area_sqm, price_mid, price_upper, price_lower,
            )

        return results

    # ──────────────────────────────────────────
    # 네이버 부동산 단지와 KB 단지 매칭
    # ──────────────────────────────────────────

    # ──────────────────────────────────────────
    # 편의 메서드: 네이버 단지 → KB시세 한번에 조회
    # ──────────────────────────────────────────

    async def get_prices_for_complex(
        self,
        complex_name: str,
        sido: str = "서울특별시",
        sigungu: str = "",
        dong: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """네이버 단지명으로 KB 단지를 매칭하고 시세를 한번에 조회한다.

        1) sido + sigungu + dong → 동-level 법정동코드 조회
        2) match_complex로 KB 단지 매칭
        3) get_all_prices로 전체 면적별 시세 조회

        Args:
            complex_name: 아파트 단지명 (네이버 기준)
            sido: 시/도 (예: "서울특별시")
            sigungu: 시/군/구 (예: "강남구")
            dong: 동 이름 (예: "대치동") - 동-level 코드 조회에 사용
            address: 주소 (미사용, 호환성 유지)

        Returns:
            (kb_complex_id 문자열, 면적별 시세 리스트) 튜플.
            매칭 실패 시 (None, [])
        """
        # 법정동코드 조회 (동-level 우선, fallback 구-level)
        lawdcd = get_lawdcd(sido, sigungu, dong)
        if not lawdcd:
            logger.warning("법정동코드 없음: %s %s %s", sido, sigungu, dong or "")
            return None, []

        # KB 단지 매칭
        matched = await self.match_complex(complex_name, lawdcd)
        if not matched:
            return None, []

        kb_id = matched.get("단지기본일련번호")
        if not kb_id:
            return None, []

        # 전체 면적별 시세 조회
        prices = await self.get_all_prices(int(kb_id))
        return str(kb_id), prices

    # ──────────────────────────────────────────
    # 네이버 부동산 단지와 KB 단지 매칭
    # ──────────────────────────────────────────

    async def match_complex(
        self,
        complex_name: str,
        lawdcd: str,
    ) -> Optional[Dict[str, Any]]:
        """네이버 부동산 단지명으로 KB 단지를 매칭한다.

        해당 지역의 단지 목록에서 이름이 가장 유사한 단지를 찾는다.

        Args:
            complex_name: 아파트 단지명 (네이버 기준)
            lawdcd: 법정동코드 (10자리)

        Returns:
            매칭된 KB 단지 정보 dict, 실패 시 None
        """
        # 해당 지역 단지 목록 조회
        complexes = await self.get_complex_list(lawdcd)
        if not complexes:
            logger.warning("KB 단지 목록 조회 실패: lawdcd=%s", lawdcd)
            return None

        # 단지명 정규화 후 매칭
        clean_target = _normalize_name(complex_name)

        best_match = None
        best_score = 0

        for cx in complexes:
            kb_name = cx.get("단지명", "")
            clean_kb = _normalize_name(kb_name)

            score = _calc_match_score(clean_target, clean_kb)
            if score > best_score:
                best_score = score
                best_match = cx

        # 최소 점수 기준 (40점 이상만 매칭 성공)
        if best_match and best_score >= 40:
            logger.info(
                "KB 매칭 성공: '%s' -> '%s' (ID=%s, score=%d)",
                complex_name,
                best_match.get("단지명", "?"),
                best_match.get("단지기본일련번호", "?"),
                best_score,
            )
            return best_match

        logger.warning("KB 매칭 실패: '%s' (best_score=%d)", complex_name, best_score)
        return None


# ──────────────────────────────────────────
# 내부 헬퍼 함수들
# ──────────────────────────────────────────

def _normalize_name(name: str) -> str:
    """단지명 정규화: 공백, 특수문자, 괄호 내용 제거."""
    # 괄호 및 괄호 내용 제거
    cleaned = re.sub(r"\([^)]*\)", "", name)
    # 숫자+단지/차 패턴 제거
    cleaned = re.sub(r"\d+단지$", "", cleaned)
    cleaned = re.sub(r"\d+차$", "", cleaned)
    # 공백, 특수문자 제거
    cleaned = re.sub(r"[^\w가-힣]", "", cleaned.lower())
    return cleaned.strip()


def _calc_match_score(target: str, candidate: str) -> int:
    """두 단지명의 매칭 점수를 계산한다.

    Args:
        target: 매칭 대상 (정규화된 단지명)
        candidate: 후보 (정규화된 KB 단지명)

    Returns:
        매칭 점수 (0~100)
    """
    if not target or not candidate:
        return 0

    # 완전 일치
    if target == candidate:
        return 100

    # 부분 포함 (한쪽이 다른쪽에 포함)
    if target in candidate or candidate in target:
        return 70

    # 공통 한글 단어 (2글자 이상)
    words_t = set(re.findall(r"[가-힣]{2,}", target))
    words_c = set(re.findall(r"[가-힣]{2,}", candidate))
    common = words_t & words_c
    if common:
        return 40

    return 0
