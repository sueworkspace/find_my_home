"""
국토교통부 아파트매매 실거래가 API 클라이언트

공공데이터포털(data.go.kr)에서 제공하는 국토교통부 아파트매매 실거래가 상세 자료 API를 호출합니다.
- API: getRTMSDataSvcAptTradeDev
- 인증: 공공데이터포털 서비스키 (DATA_GO_KR_API_KEY)
- 응답: XML 형식
- 제한: 일 1,000건
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# API 상수
# ──────────────────────────────────────────

# 국토교통부 아파트매매 실거래가 API 엔드포인트
API_BASE_URL = (
    "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade"
    "/getRTMSDataSvcAptTrade"
)

# 재시도 설정
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # 지수 백오프 기본 초

# Rate limiting: 요청 간 최소 간격 (초)
REQUEST_DELAY = 1.0

# 한 페이지당 최대 조회 건수
DEFAULT_NUM_OF_ROWS = 1000

# ──────────────────────────────────────────
# 서울 주요 구 법정동코드 (앞 5자리) 매핑
# 실제 운영에서는 DB 또는 외부 코드 테이블을 사용해야 합니다.
# ──────────────────────────────────────────
SIGUNGU_CODE_MAP: Dict[str, Dict[str, str]] = {
    "서울특별시": {
        "종로구": "11110",
        "중구": "11140",
        "용산구": "11170",
        "성동구": "11200",
        "광진구": "11215",
        "동대문구": "11230",
        "중랑구": "11260",
        "성북구": "11290",
        "강북구": "11305",
        "도봉구": "11320",
        "노원구": "11350",
        "은평구": "11380",
        "서대문구": "11410",
        "마포구": "11440",
        "양천구": "11470",
        "강서구": "11500",
        "구로구": "11530",
        "금천구": "11545",
        "영등포구": "11560",
        "동작구": "11590",
        "관악구": "11620",
        "서초구": "11650",
        "강남구": "11680",
        "송파구": "11710",
        "강동구": "11740",
    },
    "경기도": {
        "수원시": "41110",
        "성남시": "41130",
        "의정부시": "41150",
        "안양시": "41170",
        "부천시": "41190",
        "광명시": "41210",
        "평택시": "41220",
        "동두천시": "41250",
        "안산시": "41270",
        "고양시": "41280",
        "과천시": "41290",
        "구리시": "41310",
        "남양주시": "41360",
        "오산시": "41370",
        "시흥시": "41390",
        "군포시": "41410",
        "의왕시": "41430",
        "하남시": "41450",
        "용인시": "41460",
        "파주시": "41480",
        "이천시": "41500",
        "안성시": "41550",
        "김포시": "41570",
        "화성시": "41590",
        "광주시": "41610",
        "양주시": "41630",
        "포천시": "41650",
        "여주시": "41670",
    },
    "인천광역시": {
        "중구": "28110",
        "동구": "28140",
        "미추홀구": "28177",
        "연수구": "28185",
        "남동구": "28200",
        "부평구": "28237",
        "계양구": "28245",
        "서구": "28260",
    },
    "부산광역시": {
        "중구": "26110",
        "서구": "26140",
        "동구": "26170",
        "영도구": "26200",
        "부산진구": "26230",
        "동래구": "26260",
        "남구": "26290",
        "북구": "26320",
        "해운대구": "26350",
        "사하구": "26380",
        "금정구": "26410",
        "강서구": "26440",
        "연제구": "26470",
        "수영구": "26500",
        "사상구": "26530",
        "기장군": "26710",
    },
    "대구광역시": {
        "중구": "27110",
        "동구": "27140",
        "서구": "27170",
        "남구": "27200",
        "북구": "27230",
        "수성구": "27260",
        "달서구": "27290",
        "달성군": "27710",
    },
    "광주광역시": {
        "동구": "29110",
        "서구": "29140",
        "남구": "29155",
        "북구": "29170",
        "광산구": "29200",
    },
    "대전광역시": {
        "동구": "30110",
        "중구": "30140",
        "서구": "30170",
        "유성구": "30200",
        "대덕구": "30230",
    },
    "세종특별자치시": {
        "세종시": "36110",
    },
    "울산광역시": {
        "중구": "31110",
        "남구": "31140",
        "동구": "31170",
        "북구": "31200",
        "울주군": "31710",
    },
}


def get_lawd_cd(sido: str, sigungu: str) -> Optional[str]:
    """시/도와 시/군/구 이름으로 법정동코드(LAWD_CD, 5자리)를 반환한다.

    Args:
        sido: 시/도 이름 (예: "서울특별시")
        sigungu: 시/군/구 이름 (예: "강남구")

    Returns:
        법정동코드 문자열 (5자리), 없으면 None
    """
    sido_map = SIGUNGU_CODE_MAP.get(sido)
    if sido_map is None:
        logger.warning("법정동코드 매핑에 없는 시/도: %s", sido)
        return None
    code = sido_map.get(sigungu)
    if code is None:
        logger.warning("법정동코드 매핑에 없는 시/군/구: %s %s", sido, sigungu)
        return None
    return code


def _parse_xml_items(xml_text: str) -> List[Dict[str, Any]]:
    """공공데이터포털 API XML 응답에서 item 목록을 파싱한다.

    XML 구조:
      <response>
        <header>
          <resultCode>00</resultCode>
          <resultMsg>NORMAL SERVICE.</resultMsg>
        </header>
        <body>
          <items>
            <item>
              <aptDong>...</aptDong>
              <aptNm>...</aptNm>
              <dealAmount>...</dealAmount>
              ...
            </item>
          </items>
          <numOfRows>1000</numOfRows>
          <pageNo>1</pageNo>
          <totalCount>123</totalCount>
        </body>
      </response>

    Args:
        xml_text: API 응답 XML 문자열

    Returns:
        파싱된 item dict 리스트

    Raises:
        ValueError: XML 파싱 실패 또는 에러 응답인 경우
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"XML 파싱 실패: {e}")

    # 에러 코드 확인
    result_code_el = root.find(".//resultCode")
    result_msg_el = root.find(".//resultMsg")

    if result_code_el is not None and result_code_el.text not in ("00", "000"):
        msg = result_msg_el.text if result_msg_el is not None else "알 수 없는 에러"
        raise ValueError(f"API 에러 응답 (코드: {result_code_el.text}): {msg}")

    # items 파싱
    items_el = root.find(".//items")
    if items_el is None:
        # items 태그 자체가 없으면 데이터 없음
        return []

    results: List[Dict[str, Any]] = []
    for item_el in items_el.findall("item"):
        item_dict: Dict[str, Any] = {}
        for child in item_el:
            # 태그 이름을 키로, 텍스트를 값으로
            text = child.text.strip() if child.text else ""
            item_dict[child.tag] = text
        results.append(item_dict)

    return results


def _parse_total_count(xml_text: str) -> int:
    """XML 응답에서 totalCount 값을 추출한다.

    Args:
        xml_text: API 응답 XML 문자열

    Returns:
        전체 데이터 건수
    """
    try:
        root = ET.fromstring(xml_text)
        total_count_el = root.find(".//totalCount")
        if total_count_el is not None and total_count_el.text:
            return int(total_count_el.text.strip())
    except (ET.ParseError, ValueError):
        pass
    return 0


def normalize_transaction(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """API 응답의 raw item을 정규화된 거래 데이터로 변환한다.

    주요 XML 필드 매핑:
      - aptNm: 아파트명
      - aptDong: 아파트 동
      - umdNm: 법정동명
      - jibun: 지번
      - excluUseAr: 전용면적 (m2)
      - floor: 층
      - dealAmount: 거래금액 (만원, 콤마 포함 문자열)
      - dealYear: 거래년도
      - dealMonth: 거래월
      - dealDay: 거래일
      - buildYear: 건축년도
      - rgstDate: 등기일자 (YYYYMMDD, 선택)
      - cdealType: 해제여부 (선택, "O"이면 해제 거래)
      - cdealDay: 해제사유발생일 (선택)
      - slerGbn: 매도자/매수자 구분 (선택)

    Args:
        raw: XML item에서 파싱된 원시 딕셔너리

    Returns:
        정규화된 딕셔너리, 필수 필드 누락 시 None
    """
    try:
        apt_name = raw.get("aptNm", "").strip()
        if not apt_name:
            logger.debug("아파트명 누락, 건너뜀: %s", raw)
            return None

        # 거래금액: 콤마 제거 후 정수 변환 (단위: 만원)
        deal_amount_str = raw.get("dealAmount", "").strip().replace(",", "")
        if not deal_amount_str:
            logger.debug("거래금액 누락, 건너뜀: %s", raw)
            return None
        deal_amount = int(deal_amount_str)

        # 전용면적 (m2, 소수점 가능)
        area_str = raw.get("excluUseAr", "").strip()
        if not area_str:
            logger.debug("전용면적 누락, 건너뜀: %s", raw)
            return None
        area_sqm = float(area_str)

        # 층
        floor_str = raw.get("floor", "").strip()
        floor_val = int(floor_str) if floor_str else None

        # 거래일자 조합
        deal_year = raw.get("dealYear", "").strip()
        deal_month = raw.get("dealMonth", "").strip()
        deal_day = raw.get("dealDay", "").strip()
        if not (deal_year and deal_month and deal_day):
            logger.debug("거래일자 누락, 건너뜀: %s", raw)
            return None
        deal_date = datetime(
            int(deal_year),
            int(deal_month),
            int(deal_day),
        )

        # 해제 거래 여부 확인 (cdealType이 "O"이면 해제된 거래)
        cdeal_type = raw.get("cdealType", "").strip()
        if cdeal_type == "O":
            logger.debug("해제 거래 건너뜀: %s %s", apt_name, deal_date)
            return None

        return {
            "apt_name": apt_name,
            "apt_dong": raw.get("aptDong", "").strip(),
            "umd_name": raw.get("umdNm", "").strip(),
            "jibun": raw.get("jibun", "").strip(),
            "area_sqm": area_sqm,
            "floor": floor_val,
            "deal_price": deal_amount,
            "deal_date": deal_date,
            "build_year": int(raw.get("buildYear", "0").strip() or "0") or None,
        }

    except (ValueError, TypeError) as e:
        logger.warning("실거래가 데이터 정규화 실패: %s - %s", e, raw)
        return None


class RealTransactionClient:
    """국토교통부 아파트매매 실거래가 API를 호출하는 비동기 HTTP 클라이언트.

    - httpx.AsyncClient 사용
    - 요청 간 딜레이(rate limiting) 준수
    - 에러 발생 시 지수 백오프 재시도
    - XML 응답 파싱
    """

    def __init__(self, service_key: Optional[str] = None):
        """클라이언트 초기화.

        Args:
            service_key: 공공데이터포털 서비스키. None이면 settings에서 읽음.
        """
        self._client: Optional[httpx.AsyncClient] = None
        self._service_key = service_key or settings.DATA_GO_KR_API_KEY
        if not self._service_key:
            logger.warning(
                "DATA_GO_KR_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 DATA_GO_KR_API_KEY를 설정하세요."
            )

    async def _get_client(self) -> httpx.AsyncClient:
        """lazy-init으로 AsyncClient 생성."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        """클라이언트 종료."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request_raw(
        self,
        params: Dict[str, str],
    ) -> Optional[str]:
        """단일 GET 요청 실행 (재시도 로직 포함).

        Args:
            params: 쿼리 파라미터 딕셔너리

        Returns:
            XML 응답 문자열, 실패 시 None
        """
        client = await self._get_client()

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(
                    "실거래가 API 요청 [%d/%d]: params=%s",
                    attempt, MAX_RETRIES, params,
                )
                response = await client.get(API_BASE_URL, params=params)

                if response.status_code == 200:
                    return response.text

                if response.status_code == 429:
                    # Rate limit 초과 - 더 긴 대기
                    wait = RETRY_BACKOFF_BASE ** attempt * 2
                    logger.warning(
                        "Rate limited (429). %.1f초 후 재시도 (%d/%d)",
                        wait, attempt, MAX_RETRIES,
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code in (403, 401):
                    logger.error(
                        "인증 실패 (%d). 서비스키를 확인하세요.",
                        response.status_code,
                    )
                    return None

                # 그 외 에러
                logger.warning(
                    "HTTP %d 응답 (%d/%d)",
                    response.status_code, attempt, MAX_RETRIES,
                )

            except httpx.TimeoutException:
                logger.warning(
                    "타임아웃 (%d/%d)", attempt, MAX_RETRIES,
                )
            except httpx.HTTPError as e:
                logger.warning(
                    "HTTP 에러: %s (%d/%d)", str(e), attempt, MAX_RETRIES,
                )

            # 지수 백오프 대기
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.info("%.1f초 후 재시도...", wait)
                await asyncio.sleep(wait)

        logger.error("최대 재시도 횟수 초과")
        return None

    async def _throttle(self):
        """요청 간 딜레이 적용 (rate limiting)."""
        await asyncio.sleep(REQUEST_DELAY)

    # ──────────────────────────────────────────
    # 공개 메서드
    # ──────────────────────────────────────────

    async def fetch_transactions(
        self,
        lawd_cd: str,
        deal_ymd: str,
        page_no: int = 1,
        num_of_rows: int = DEFAULT_NUM_OF_ROWS,
    ) -> List[Dict[str, Any]]:
        """특정 지역/기간의 아파트매매 실거래가를 조회한다.

        Args:
            lawd_cd: 법정동코드 앞 5자리 (예: "11680" = 서울 강남구)
            deal_ymd: 계약년월 6자리 (예: "202401" = 2024년 1월)
            page_no: 페이지 번호 (기본 1)
            num_of_rows: 한 페이지 조회 건수 (기본 1000)

        Returns:
            정규화된 거래 데이터 리스트
        """
        params = {
            "serviceKey": self._service_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "pageNo": str(page_no),
            "numOfRows": str(num_of_rows),
        }

        await self._throttle()
        xml_text = await self._request_raw(params)
        if xml_text is None:
            return []

        try:
            raw_items = _parse_xml_items(xml_text)
        except ValueError as e:
            logger.error("XML 파싱 실패: %s", e)
            return []

        # 각 item을 정규화
        results: List[Dict[str, Any]] = []
        for raw in raw_items:
            normalized = normalize_transaction(raw)
            if normalized is not None:
                results.append(normalized)

        logger.info(
            "실거래가 조회 완료: LAWD_CD=%s, DEAL_YMD=%s, "
            "원시=%d건, 정규화=%d건",
            lawd_cd, deal_ymd, len(raw_items), len(results),
        )
        return results

    async def fetch_all_transactions(
        self,
        lawd_cd: str,
        deal_ymd: str,
    ) -> List[Dict[str, Any]]:
        """특정 지역/기간의 모든 아파트매매 실거래가를 페이지네이션으로 조회한다.

        totalCount가 numOfRows보다 크면 다음 페이지를 자동으로 조회한다.

        Args:
            lawd_cd: 법정동코드 앞 5자리
            deal_ymd: 계약년월 6자리

        Returns:
            전체 정규화된 거래 데이터 리스트
        """
        all_results: List[Dict[str, Any]] = []
        page_no = 1

        while True:
            params = {
                "serviceKey": self._service_key,
                "LAWD_CD": lawd_cd,
                "DEAL_YMD": deal_ymd,
                "pageNo": str(page_no),
                "numOfRows": str(DEFAULT_NUM_OF_ROWS),
            }

            await self._throttle()
            xml_text = await self._request_raw(params)
            if xml_text is None:
                break

            try:
                raw_items = _parse_xml_items(xml_text)
                total_count = _parse_total_count(xml_text)
            except ValueError as e:
                logger.error("XML 파싱 실패 (page %d): %s", page_no, e)
                break

            # 정규화 후 결과에 추가
            for raw in raw_items:
                normalized = normalize_transaction(raw)
                if normalized is not None:
                    all_results.append(normalized)

            # 다음 페이지 확인
            fetched_so_far = page_no * DEFAULT_NUM_OF_ROWS
            if fetched_so_far >= total_count or len(raw_items) == 0:
                break

            page_no += 1

        logger.info(
            "전체 실거래가 조회 완료: LAWD_CD=%s, DEAL_YMD=%s, 총 %d건",
            lawd_cd, deal_ymd, len(all_results),
        )
        return all_results

    async def fetch_by_region(
        self,
        sido: str,
        sigungu: str,
        deal_ymd: str,
    ) -> List[Dict[str, Any]]:
        """시/도 + 시/군/구 이름으로 실거래가를 조회한다.

        내부적으로 법정동코드를 조회한 뒤 API를 호출한다.

        Args:
            sido: 시/도 이름 (예: "서울특별시")
            sigungu: 시/군/구 이름 (예: "강남구")
            deal_ymd: 계약년월 6자리 (예: "202401")

        Returns:
            정규화된 거래 데이터 리스트, 코드 매핑 실패 시 빈 리스트
        """
        lawd_cd = get_lawd_cd(sido, sigungu)
        if lawd_cd is None:
            logger.error(
                "법정동코드 조회 실패: %s %s", sido, sigungu,
            )
            return []

        return await self.fetch_all_transactions(lawd_cd, deal_ymd)
