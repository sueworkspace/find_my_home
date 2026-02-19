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
# 전국 시/군/구 법정동코드 매핑 (kbland.kr용)
# 구-level 코드 (fallback용): 5자리 SIGUNGU_CODE + "00000" = 10자리
# ──────────────────────────────────────────
LAWDCD_MAP: Dict[str, Dict[str, str]] = {
    "서울특별시": {
        "종로구":   "1111000000",
        "중구":     "1114000000",
        "용산구":   "1117000000",
        "성동구":   "1120000000",
        "광진구":   "1121500000",
        "동대문구": "1123000000",
        "중랑구":   "1126000000",
        "성북구":   "1129000000",
        "강북구":   "1130500000",
        "도봉구":   "1132000000",
        "노원구":   "1135000000",
        "은평구":   "1138000000",
        "서대문구": "1141000000",
        "마포구":   "1144000000",
        "양천구":   "1147000000",
        "강서구":   "1150000000",
        "구로구":   "1153000000",
        "금천구":   "1154500000",
        "영등포구": "1156000000",
        "동작구":   "1159000000",
        "관악구":   "1162000000",
        "서초구":   "1165000000",
        "강남구":   "1168000000",
        "송파구":   "1171000000",
        "강동구":   "1174000000",
    },
    "경기도": {
        "수원시":   "4111000000",
        "성남시":   "4113000000",
        "의정부시": "4115000000",
        "안양시":   "4117000000",
        "부천시":   "4119000000",
        "광명시":   "4121000000",
        "평택시":   "4122000000",
        "동두천시": "4125000000",
        "안산시":   "4127000000",
        "고양시":   "4128000000",
        "과천시":   "4129000000",
        "구리시":   "4131000000",
        "남양주시": "4136000000",
        "오산시":   "4137000000",
        "시흥시":   "4139000000",
        "군포시":   "4141000000",
        "의왕시":   "4143000000",
        "하남시":   "4145000000",
        "용인시":   "4146000000",
        "파주시":   "4148000000",
        "이천시":   "4150000000",
        "안성시":   "4155000000",
        "김포시":   "4157000000",
        "화성시":   "4159000000",
        "광주시":   "4161000000",
        "양주시":   "4163000000",
        "포천시":   "4165000000",
        "여주시":   "4167000000",
    },
    "인천광역시": {
        "중구":     "2811000000",
        "동구":     "2814000000",
        "미추홀구": "2817700000",
        "연수구":   "2818500000",
        "남동구":   "2820000000",
        "부평구":   "2823700000",
        "계양구":   "2824500000",
        "서구":     "2826000000",
    },
    "부산광역시": {
        "중구":     "2611000000",
        "서구":     "2614000000",
        "동구":     "2617000000",
        "영도구":   "2620000000",
        "부산진구": "2623000000",
        "동래구":   "2626000000",
        "남구":     "2629000000",
        "북구":     "2632000000",
        "해운대구": "2635000000",
        "사하구":   "2638000000",
        "금정구":   "2641000000",
        "강서구":   "2644000000",
        "연제구":   "2647000000",
        "수영구":   "2650000000",
        "사상구":   "2653000000",
        "기장군":   "2671000000",
    },
    "대구광역시": {
        "중구":   "2711000000",
        "동구":   "2714000000",
        "서구":   "2717000000",
        "남구":   "2720000000",
        "북구":   "2723000000",
        "수성구": "2726000000",
        "달서구": "2729000000",
        "달성군": "2771000000",
    },
    "광주광역시": {
        "동구":   "2911000000",
        "서구":   "2914000000",
        "남구":   "2915500000",
        "북구":   "2917000000",
        "광산구": "2920000000",
    },
    "대전광역시": {
        "동구":   "3011000000",
        "중구":   "3014000000",
        "서구":   "3017000000",
        "유성구": "3020000000",
        "대덕구": "3023000000",
    },
    "세종특별자치시": {
        "세종시": "3611000000",
    },
    "울산광역시": {
        "중구":   "3111000000",
        "남구":   "3114000000",
        "동구":   "3117000000",
        "북구":   "3120000000",
        "울주군": "3171000000",
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
        # ── Sprint 10: 동-level 세분화 (기존 구-level 폴백으로 매칭 실패 86/74/56건) ──
        "종로구": {
            "청운동": "1111010100",
            "신교동": "1111010200",
            "궁정동": "1111010300",
            "효자동": "1111010400",
            "창성동": "1111010500",
            "통의동": "1111010600",
            "적선동": "1111010700",
            "통인동": "1111010800",
            "누상동": "1111010900",
            "누하동": "1111011000",
            "옥인동": "1111011100",
            "체부동": "1111011200",
            "필운동": "1111011300",
            "내자동": "1111011400",
            "사직동": "1111011500",
            "도렴동": "1111011600",
            "당주동": "1111011700",
            "내수동": "1111011800",
            "세종로": "1111011900",
            "신문로1가": "1111012000",
            "신문로2가": "1111012100",
            "청진동": "1111012200",
            "서린동": "1111012300",
            "수송동": "1111012400",
            "중학동": "1111012500",
            "종로1가": "1111012600",
            "공평동": "1111012700",
            "관훈동": "1111012800",
            "견지동": "1111012900",
            "와룡동": "1111013000",
            "권농동": "1111013100",
            "운니동": "1111013200",
            "익선동": "1111013300",
            "경운동": "1111013400",
            "관철동": "1111013500",
            "인사동": "1111013600",
            "낙원동": "1111013700",
            "종로2가": "1111013800",
            "팔판동": "1111013900",
            "삼청동": "1111014000",
            "안국동": "1111014100",
            "소격동": "1111014200",
            "화동": "1111014300",
            "사간동": "1111014400",
            "송현동": "1111014500",
            "가회동": "1111014600",
            "재동": "1111014700",
            "계동": "1111014800",
            "원서동": "1111014900",
            "훈정동": "1111015000",
            "묘동": "1111015100",
            "봉익동": "1111015200",
            "돈의동": "1111015300",
            "장사동": "1111015400",
            "관수동": "1111015500",
            "종로3가": "1111015600",
            "인의동": "1111015700",
            "예지동": "1111015800",
            "원남동": "1111015900",
            "연지동": "1111016000",
            "종로4가": "1111016100",
            "효제동": "1111016200",
            "종로5가": "1111016300",
            "종로6가": "1111016400",
            "이화동": "1111016500",
            "연건동": "1111016600",
            "충신동": "1111016700",
            "동숭동": "1111016800",
            "혜화동": "1111016900",
            "명륜1가": "1111017000",
            "명륜2가": "1111017100",
            "명륜4가": "1111017200",
            "명륜3가": "1111017300",
            "창신동": "1111017400",
            "숭인동": "1111017500",
            "교남동": "1111017600",
            "평동": "1111017700",
            "송월동": "1111017800",
            "홍파동": "1111017900",
            "교북동": "1111018000",
            "행촌동": "1111018100",
            "구기동": "1111018200",
            "평창동": "1111018300",
            "부암동": "1111018400",
            "홍지동": "1111018500",
            "신영동": "1111018600",
            "무악동": "1111018700",
        },
        "중구": {
            "무교동": "1114010100",
            "다동": "1114010200",
            "태평로1가": "1114010300",
            "을지로1가": "1114010400",
            "을지로2가": "1114010500",
            "남대문로1가": "1114010600",
            "삼각동": "1114010700",
            "수하동": "1114010800",
            "장교동": "1114010900",
            "수표동": "1114011000",
            "소공동": "1114011100",
            "남창동": "1114011200",
            "북창동": "1114011300",
            "태평로2가": "1114011400",
            "남대문로2가": "1114011500",
            "남대문로3가": "1114011600",
            "남대문로4가": "1114011700",
            "남대문로5가": "1114011800",
            "봉래동1가": "1114011900",
            "봉래동2가": "1114012000",
            "회현동1가": "1114012100",
            "회현동2가": "1114012200",
            "회현동3가": "1114012300",
            "충무로1가": "1114012400",
            "충무로2가": "1114012500",
            "명동1가": "1114012600",
            "명동2가": "1114012700",
            "남산동1가": "1114012800",
            "남산동2가": "1114012900",
            "남산동3가": "1114013000",
            "저동1가": "1114013100",
            "충무로4가": "1114013200",
            "충무로5가": "1114013300",
            "인현동2가": "1114013400",
            "예관동": "1114013500",
            "묵정동": "1114013600",
            "필동1가": "1114013700",
            "필동2가": "1114013800",
            "필동3가": "1114013900",
            "남학동": "1114014000",
            "주자동": "1114014100",
            "예장동": "1114014200",
            "장충동1가": "1114014300",
            "장충동2가": "1114014400",
            "광희동1가": "1114014500",
            "광희동2가": "1114014600",
            "쌍림동": "1114014700",
            "을지로6가": "1114014800",
            "을지로7가": "1114014900",
            "을지로4가": "1114015000",
            "을지로5가": "1114015100",
            "주교동": "1114015200",
            "방산동": "1114015300",
            "오장동": "1114015400",
            "을지로3가": "1114015500",
            "입정동": "1114015600",
            "산림동": "1114015700",
            "충무로3가": "1114015800",
            "초동": "1114015900",
            "인현동1가": "1114016000",
            "저동2가": "1114016100",
            "신당동": "1114016200",
            "흥인동": "1114016300",
            "무학동": "1114016400",
            "황학동": "1114016500",
            "서소문동": "1114016600",
            "정동": "1114016700",
            "순화동": "1114016800",
            "의주로1가": "1114016900",
            "충정로1가": "1114017000",
            "중림동": "1114017100",
            "의주로2가": "1114017200",
            "만리동1가": "1114017300",
            "만리동2가": "1114017400",
        },
        "용산구": {
            "후암동": "1117010100",
            "용산동2가": "1117010200",
            "용산동4가": "1117010300",
            "갈월동": "1117010400",
            "남영동": "1117010500",
            "용산동1가": "1117010600",
            "동자동": "1117010700",
            "서계동": "1117010800",
            "청파동1가": "1117010900",
            "청파동2가": "1117011000",
            "청파동3가": "1117011100",
            "원효로1가": "1117011200",
            "원효로2가": "1117011300",
            "신창동": "1117011400",
            "산천동": "1117011500",
            "청암동": "1117011600",
            "원효로3가": "1117011700",
            "원효로4가": "1117011800",
            "효창동": "1117011900",
            "도원동": "1117012000",
            "용문동": "1117012100",
            "문배동": "1117012200",
            "신계동": "1117012300",
            "한강로1가": "1117012400",
            "한강로2가": "1117012500",
            "용산동3가": "1117012600",
            "용산동5가": "1117012700",
            "한강로3가": "1117012800",
            "이촌동": "1117012900",
            "이태원동": "1117013000",
            "한남동": "1117013100",
            "동빙고동": "1117013200",
            "서빙고동": "1117013300",
            "주성동": "1117013400",
            "용산동6가": "1117013500",
            "보광동": "1117013600",
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
        dong_code: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """네이버 단지명으로 KB 단지를 매칭하고 시세를 한번에 조회한다.

        1) dong_code가 있으면 직접 사용, 없으면 sido+sigungu+dong으로 조회
        2) match_complex로 KB 단지 매칭
        3) get_all_prices로 전체 면적별 시세 조회

        Args:
            complex_name: 아파트 단지명 (네이버 기준)
            sido: 시/도 (예: "서울특별시")
            sigungu: 시/군/구 (예: "강남구")
            dong: 동 이름 (예: "대치동") - 동-level 코드 조회에 사용
            dong_code: 법정동코드 10자리 (DB에서 전달, 우선 사용)
            address: 주소 (미사용, 호환성 유지)

        Returns:
            (kb_complex_id 문자열, 면적별 시세 리스트) 튜플.
            매칭 실패 시 (None, [])
        """
        # 법정동코드 조회: dong_code 우선, fallback: 동 이름 → DONG_LAWDCD_MAP
        lawdcd = dong_code or get_lawdcd(sido, sigungu, dong)
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
