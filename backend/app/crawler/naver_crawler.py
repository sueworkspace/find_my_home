"""
네이버 부동산 아파트 매매 매물 크롤러

지역(시/도, 시/군/구) 기반으로 아파트 단지를 탐색하고,
각 단지의 매매 매물을 수집하여 DB에 저장합니다.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from sqlalchemy.orm import Session

from sqlalchemy import func as sa_func

from app.crawler.naver_client import NaverLandClient
from app.models.apartment import ApartmentComplex, Listing
from app.models.database import SessionLocal
from config.settings import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────
# 법정동 코드 매핑 (시/도 -> 시/군/구)
# 네이버 부동산 API에서 사용하는 cortarNo 기반
# ──────────────────────────────────────────
# 시/도 코드 (상위 2자리 + 0 패딩)
SIDO_CODES: Dict[str, str] = {
    "서울특별시": "1100000000",
    "부산광역시": "2600000000",
    "대구광역시": "2700000000",
    "인천광역시": "2800000000",
    "광주광역시": "2900000000",
    "대전광역시": "3000000000",
    "울산광역시": "3100000000",
    "세종특별자치시": "3600000000",
    "경기도": "4100000000",
    "강원특별자치도": "4200000000",
    "충청북도": "4300000000",
    "충청남도": "4400000000",
    "전북특별자치도": "4500000000",
    "전라남도": "4600000000",
    "경상북도": "4700000000",
    "경상남도": "4800000000",
    "제주특별자치도": "5000000000",
}


def _parse_price(price_str: Optional[str]) -> Optional[int]:
    """네이버 부동산 가격 문자열을 정수(만원 단위)로 변환.

    예시:
        '9억 5,000' -> 95000
        '12억' -> 120000
        '8,500' -> 8500
    """
    if not price_str:
        return None

    price_str = price_str.strip().replace(",", "")

    try:
        if "억" in price_str:
            parts = price_str.split("억")
            억 = int(parts[0].strip()) * 10000
            나머지 = 0
            if len(parts) > 1 and parts[1].strip():
                나머지 = int(parts[1].strip())
            return 억 + 나머지
        else:
            return int(price_str)
    except (ValueError, IndexError):
        logger.warning("가격 파싱 실패: '%s'", price_str)
        return None


def _parse_area(area_str: Union[str, float, None]) -> Optional[float]:
    """면적 문자열을 float(제곱미터)로 변환."""
    if area_str is None:
        return None
    try:
        return float(str(area_str).replace("㎡", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_floor(floor_str: Union[str, int, None]) -> Optional[int]:
    """층수 문자열을 정수로 변환.

    예시:
        '15' -> 15, '15층' -> 15
        '저' -> None, '고' -> None, '중' -> None
        '15/20' -> 15 (슬래시 앞이 해당 층)
    """
    if floor_str is None:
        return None
    s = str(floor_str).replace("층", "").strip()
    # "저/16", "고/20" 등 한글 층 표현 → None
    if s in ("저", "중", "고", ""):
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """날짜 문자열을 datetime으로 변환.

    예시:
        '20260215' -> 2026-02-15
        '2026-02-15' -> 2026-02-15
        '2026.02.15' -> 2026-02-15
        '26.02.14' -> 2026-02-14 (YY.MM.DD 2자리 연도)
    """
    if not date_str:
        return None
    date_str = date_str.strip()

    # "26.02.14" 형식 (YY.MM.DD) — 네이버 모바일 API cfmYmd
    if len(date_str) == 8 and date_str[2] == "." and date_str[5] == ".":
        try:
            return datetime.strptime(date_str, "%y.%m.%d")
        except ValueError:
            pass

    # 구분자 제거 후 YYYYMMDD 파싱
    cleaned = date_str.replace(".", "").replace("-", "")
    try:
        return datetime.strptime(cleaned, "%Y%m%d")
    except ValueError:
        return None


class NaverCrawler:
    """네이버 부동산 매물 크롤러.

    사용법:
        crawler = NaverCrawler()
        await crawler.crawl_region("서울특별시", "강남구")
        await crawler.close()

    또는 전체 크롤링:
        await crawler.crawl_all_target_regions()
    """

    def __init__(self, target_regions: Optional[List[Dict[str, str]]] = None):
        """
        Args:
            target_regions: 크롤링 대상 지역 리스트.
                예: [{"sido": "서울특별시", "sigungu": "강남구"}, ...]
                None이면 settings에서 로드.
        """
        self.client = NaverLandClient()
        self.target_regions = target_regions or []
        self._stats = {
            "complexes_found": 0,
            "articles_found": 0,
            "articles_saved": 0,
            "errors": 0,
        }

    async def close(self):
        """리소스 정리."""
        await self.client.close()

    def _reset_stats(self):
        """통계 초기화."""
        for key in self._stats:
            self._stats[key] = 0

    # ──────────────────────────────────────────
    # 지역 코드 탐색
    # ──────────────────────────────────────────

    async def _find_sigungu_code(self, sido: str, sigungu: str) -> Optional[str]:
        """시/도 이름과 시/군/구 이름으로 법정동 코드(cortarNo)를 찾는다.

        1) SIDO_CODES에서 시/도 코드 확인
        2) 해당 시/도의 하위 지역 목록 API 호출
        3) sigungu 이름과 매칭되는 코드 반환
        """
        sido_code = SIDO_CODES.get(sido)
        if not sido_code:
            logger.error("알 수 없는 시/도: %s", sido)
            return None

        # 시/도 하위 지역(시/군/구) 목록 조회 (정규화된 리스트 반환)
        regions = await self.client.get_sub_regions(sido_code)
        if not regions:
            logger.error("시/도 하위 지역 조회 실패: %s", sido)
            return None

        for region in regions:
            cortar_name = region.get("cortarName", "")
            if sigungu in cortar_name or cortar_name in sigungu:
                code = region.get("cortarNo")
                logger.info("지역 코드 발견: %s %s -> %s", sido, sigungu, code)
                return code

        logger.error("시/군/구를 찾을 수 없음: %s %s", sido, sigungu)
        return None

    # ──────────────────────────────────────────
    # 단지 목록 수집
    # ──────────────────────────────────────────

    async def _get_dong_list(self, sigungu_code: str) -> List[Dict]:
        """시/군/구 코드로 하위 읍/면/동 목록을 가져온다."""
        regions = await self.client.get_sub_regions(sigungu_code)
        if not regions:
            return []
        return regions

    async def _get_complexes_in_dong(self, dong_code: str) -> List[Dict]:
        """동 코드의 아파트 단지 목록을 모든 페이지에서 수집."""
        all_complexes: List[Dict] = []
        page = 1

        while True:
            data = await self.client.get_complex_list_in_region(dong_code, page=page)
            if not data:
                break

            complexes = data.get("complexList", [])
            if not complexes:
                break

            all_complexes.extend(complexes)
            logger.debug("동 %s 페이지 %d: %d개 단지", dong_code, page, len(complexes))

            # 다음 페이지가 있는지 확인
            total = data.get("totalCount", 0)
            if len(all_complexes) >= total:
                break
            page += 1

        return all_complexes

    # ──────────────────────────────────────────
    # 매물 수집
    # ──────────────────────────────────────────

    async def _get_all_articles_for_complex(self, complex_no: str) -> List[Dict]:
        """단지의 매매 매물을 모든 페이지에서 수집."""
        all_articles: List[Dict] = []
        page = 1

        while True:
            data = await self.client.get_articles_for_complex(
                complex_no=complex_no,
                trade_type="A1",  # 매매
                page=page,
            )
            if not data:
                break

            articles = data.get("articleList", [])
            if not articles:
                break

            all_articles.extend(articles)

            total = data.get("totalCount", 0)
            if len(all_articles) >= total:
                break
            page += 1

        return all_articles

    # ──────────────────────────────────────────
    # DB 저장
    # ──────────────────────────────────────────

    def _upsert_complex(
        self,
        db: Session,
        complex_data: Dict[str, Any],
        sido: str,
        sigungu: str,
    ) -> Optional[ApartmentComplex]:
        """단지 정보를 DB에 upsert (insert or update)."""
        complex_no = str(complex_data.get("complexNo", ""))
        if not complex_no:
            return None

        existing = db.query(ApartmentComplex).filter(
            ApartmentComplex.naver_complex_no == complex_no
        ).first()

        name = complex_data.get("complexName", "")
        address = complex_data.get("address", "")
        dong = complex_data.get("cortarAddress", "")
        total_units = complex_data.get("totalHouseholdCount")
        built_year = complex_data.get("useApproveYmd", "")
        lat = complex_data.get("latitude")
        lng = complex_data.get("longitude")

        # built_year 파싱: "20050101" -> 2005
        if built_year and len(str(built_year)) >= 4:
            try:
                built_year = int(str(built_year)[:4])
            except ValueError:
                built_year = None
        else:
            built_year = None

        if total_units:
            try:
                total_units = int(total_units)
            except (ValueError, TypeError):
                total_units = None

        if existing:
            # 기존 레코드 업데이트
            existing.name = name or existing.name
            existing.address = address or existing.address
            existing.sido = sido
            existing.sigungu = sigungu
            existing.dong = dong or existing.dong
            if total_units:
                existing.total_units = total_units
            if built_year:
                existing.built_year = built_year
            if lat:
                existing.lat = float(lat)
            if lng:
                existing.lng = float(lng)
            return existing
        else:
            # 신규 삽입
            new_complex = ApartmentComplex(
                naver_complex_no=complex_no,
                name=name,
                address=address,
                sido=sido,
                sigungu=sigungu,
                dong=dong,
                total_units=total_units,
                built_year=built_year,
                lat=float(lat) if lat else None,
                lng=float(lng) if lng else None,
            )
            db.add(new_complex)
            db.flush()  # ID 생성을 위해 flush
            return new_complex

    def _upsert_listing(
        self,
        db: Session,
        article: Dict[str, Any],
        complex_obj: ApartmentComplex,
    ) -> Optional[Listing]:
        """매물 정보를 DB에 upsert."""
        article_id = str(article.get("articleNo", ""))
        if not article_id:
            return None

        # 가격 파싱 - dealOrWarrantPrc 또는 dealPrice 필드
        price_str = article.get("dealOrWarrantPrc") or article.get("dealPrice", "")
        asking_price = _parse_price(str(price_str))
        if asking_price is None:
            logger.warning("매물 %s 가격 파싱 실패: %s", article_id, price_str)
            return None

        # 면적 파싱 - area2(전용면적) 우선, 없으면 area1(공급면적)
        area = _parse_area(article.get("area2") or article.get("area1"))
        if area is None:
            logger.warning("매물 %s 면적 파싱 실패", article_id)
            return None

        floor = _parse_floor(article.get("floorInfo", "").split("/")[0] if article.get("floorInfo") else None)
        dong = article.get("buildingName", "")
        registered_at = _parse_datetime(article.get("articleConfirmYmd"))

        # 매물 URL 생성
        listing_url = f"https://m.land.naver.com/article/info/{article_id}"

        existing = db.query(Listing).filter(
            Listing.naver_article_id == article_id
        ).first()

        if existing:
            # 기존 매물 업데이트 (가격 변동 등)
            existing.asking_price = asking_price
            existing.is_active = True
            existing.floor = floor or existing.floor
            existing.dong = dong or existing.dong
            existing.area_sqm = area
            return existing
        else:
            new_listing = Listing(
                naver_article_id=article_id,
                complex_id=complex_obj.id,
                dong=dong,
                area_sqm=area,
                floor=floor,
                asking_price=asking_price,
                listing_url=listing_url,
                registered_at=registered_at,
                is_active=True,
            )
            db.add(new_listing)
            return new_listing

    def _deactivate_missing_listings(
        self,
        db: Session,
        complex_id: int,
        active_article_ids: Set[str],
    ):
        """API에서 더 이상 조회되지 않는 매물을 비활성화."""
        stale_listings = db.query(Listing).filter(
            Listing.complex_id == complex_id,
            Listing.is_active == True,  # noqa: E712
            Listing.naver_article_id.notin_(active_article_ids) if active_article_ids else True,
        ).all()

        for listing in stale_listings:
            listing.is_active = False
            logger.debug("매물 비활성화: %s", listing.naver_article_id)

    # ──────────────────────────────────────────
    # 메인 크롤링 로직
    # ──────────────────────────────────────────

    async def crawl_complex(
        self,
        db: Session,
        complex_data: dict,
        sido: str,
        sigungu: str,
    ) -> int:
        """단일 단지의 매물을 크롤링하여 DB에 저장.

        Returns:
            저장된 매물 수
        """
        complex_no = str(complex_data.get("complexNo", ""))
        complex_name = complex_data.get("complexName", "알 수 없음")

        # 단지 정보 upsert
        complex_obj = self._upsert_complex(db, complex_data, sido, sigungu)
        if not complex_obj:
            return 0

        # 매물 목록 수집
        articles = await self._get_all_articles_for_complex(complex_no)
        if not articles:
            logger.debug("단지 %s(%s): 매매 매물 없음", complex_name, complex_no)
            # 매물이 없으면 기존 활성 매물 비활성화
            self._deactivate_missing_listings(db, complex_obj.id, set())
            return 0

        self._stats["articles_found"] += len(articles)
        saved = 0
        active_ids: Set[str] = set()

        for article in articles:
            article_id = str(article.get("articleNo", ""))
            if article_id:
                active_ids.add(article_id)

            listing = self._upsert_listing(db, article, complex_obj)
            if listing:
                saved += 1

        # 더 이상 없는 매물 비활성화
        self._deactivate_missing_listings(db, complex_obj.id, active_ids)

        self._stats["articles_saved"] += saved
        logger.info(
            "단지 %s(%s): %d개 매물 중 %d개 저장",
            complex_name, complex_no, len(articles), saved,
        )
        return saved

    async def crawl_region(self, sido: str, sigungu: str) -> dict:
        """특정 시/도, 시/군/구의 모든 아파트 매물 크롤링.

        Args:
            sido: 시/도 이름 (예: "서울특별시")
            sigungu: 시/군/구 이름 (예: "강남구")

        Returns:
            크롤링 통계 dict
        """
        logger.info("===== 크롤링 시작: %s %s =====", sido, sigungu)
        self._reset_stats()

        # 1) 시/군/구 코드 찾기
        sigungu_code = await self._find_sigungu_code(sido, sigungu)
        if not sigungu_code:
            logger.error("시/군/구 코드를 찾을 수 없어 크롤링 중단: %s %s", sido, sigungu)
            return self._stats.copy()

        # 2) 하위 동 목록 가져오기
        dong_list = await self._get_dong_list(sigungu_code)
        if not dong_list:
            logger.warning("동 목록이 비어있음: %s %s", sido, sigungu)
            return self._stats.copy()

        logger.info("%s %s: %d개 동 발견", sido, sigungu, len(dong_list))

        # 3) 동별로 단지 탐색 및 매물 크롤링
        db = SessionLocal()
        try:
            for dong_info in dong_list:
                dong_code = dong_info.get("cortarNo", "")
                dong_name = dong_info.get("cortarName", "")
                logger.info("--- 동 크롤링: %s (%s) ---", dong_name, dong_code)

                complexes = await self._get_complexes_in_dong(dong_code)
                if not complexes:
                    logger.debug("동 %s: 아파트 단지 없음", dong_name)
                    continue

                self._stats["complexes_found"] += len(complexes)
                logger.info("동 %s: %d개 단지 발견", dong_name, len(complexes))

                for complex_data in complexes:
                    try:
                        await self.crawl_complex(db, complex_data, sido, sigungu)
                    except Exception as e:
                        self._stats["errors"] += 1
                        complex_name = complex_data.get("complexName", "?")
                        logger.error(
                            "단지 크롤링 실패 (%s): %s",
                            complex_name, str(e),
                            exc_info=True,
                        )

            # 모든 동 처리 완료 후 커밋
            db.commit()
            logger.info(
                "===== 크롤링 완료: %s %s =====\n"
                "  단지: %d개, 매물 발견: %d개, 저장: %d개, 에러: %d건",
                sido, sigungu,
                self._stats["complexes_found"],
                self._stats["articles_found"],
                self._stats["articles_saved"],
                self._stats["errors"],
            )

        except Exception as e:
            db.rollback()
            logger.error("크롤링 중 치명적 에러: %s", str(e), exc_info=True)
            raise
        finally:
            db.close()

        return self._stats.copy()

    async def crawl_all_target_regions(self) -> List[Dict]:
        """설정된 모든 대상 지역을 순차적으로 크롤링.

        Returns:
            지역별 크롤링 통계 리스트
        """
        results = []

        if not self.target_regions:
            logger.warning("크롤링 대상 지역이 설정되지 않음")
            return results

        logger.info("전체 크롤링 시작: %d개 지역", len(self.target_regions))

        for region in self.target_regions:
            sido = region.get("sido", "")
            sigungu = region.get("sigungu", "")

            if not sido or not sigungu:
                logger.warning("잘못된 지역 설정: %s", region)
                continue

            try:
                stats = await self.crawl_region(sido, sigungu)
                results.append({
                    "sido": sido,
                    "sigungu": sigungu,
                    **stats,
                })
            except Exception as e:
                logger.error("지역 크롤링 실패 (%s %s): %s", sido, sigungu, str(e))
                results.append({
                    "sido": sido,
                    "sigungu": sigungu,
                    "error": str(e),
                })

        logger.info("전체 크롤링 완료: %d개 지역 처리", len(results))
        return results

    # ──────────────────────────────────────────
    # 증분 크롤링 (Incremental)
    # ──────────────────────────────────────────

    def _get_active_listing_counts(
        self,
        db: Session,
        complex_nos: List[str],
    ) -> Dict[str, int]:
        """DB에서 단지별 활성 매물 수를 조회.

        Args:
            db: DB 세션
            complex_nos: 네이버 단지번호 리스트

        Returns:
            {naver_complex_no: 활성 매물 수} 딕셔너리
        """
        if not complex_nos:
            return {}

        # 단지번호 → complex_id 매핑 조회
        rows = (
            db.query(
                ApartmentComplex.naver_complex_no,
                sa_func.count(Listing.id),
            )
            .outerjoin(
                Listing,
                (Listing.complex_id == ApartmentComplex.id) & (Listing.is_active == True),  # noqa: E712
            )
            .filter(ApartmentComplex.naver_complex_no.in_(complex_nos))
            .group_by(ApartmentComplex.naver_complex_no)
            .all()
        )
        return {row[0]: row[1] for row in rows}

    def _bulk_deactivate_listings(
        self,
        db: Session,
        complex_nos: List[str],
    ) -> int:
        """dealCnt=0인 단지의 모든 활성 매물을 일괄 비활성화.

        Args:
            db: DB 세션
            complex_nos: 비활성화 대상 단지번호 리스트

        Returns:
            비활성화된 매물 수
        """
        if not complex_nos:
            return 0

        # 해당 단지들의 complex_id 조회
        complex_ids = [
            row[0] for row in
            db.query(ApartmentComplex.id)
            .filter(ApartmentComplex.naver_complex_no.in_(complex_nos))
            .all()
        ]
        if not complex_ids:
            return 0

        # 활성 매물 일괄 비활성화
        count = (
            db.query(Listing)
            .filter(
                Listing.complex_id.in_(complex_ids),
                Listing.is_active == True,  # noqa: E712
            )
            .update({"is_active": False}, synchronize_session="fetch")
        )
        logger.info("일괄 비활성화: %d개 단지, %d개 매물", len(complex_nos), count)
        return count

    async def crawl_region_incremental(self, sido: str, sigungu: str) -> dict:
        """증분 크롤링: 변화가 감지된 단지만 매물 상세 수집.

        Phase 1: 동별 단지 목록 수집 (cheap, ~55 API 호출)
        Phase 2: 200세대 미만 필터링
        Phase 3: dealCnt=0 단지 매물 일괄 비활성화
        Phase 4: dealCnt 변화 감지 → 대상만 상세 크롤링

        Args:
            sido: 시/도 이름
            sigungu: 시/군/구 이름

        Returns:
            크롤링 통계 dict
        """
        logger.info("===== [증분] 크롤링 시작: %s %s =====", sido, sigungu)
        self._reset_stats()
        min_households = settings.MIN_HOUSEHOLD_COUNT

        # Phase 1: 동별 단지 목록 수집
        sigungu_code = await self._find_sigungu_code(sido, sigungu)
        if not sigungu_code:
            logger.error("[증분] 시/군/구 코드 못 찾음: %s %s", sido, sigungu)
            return self._stats.copy()

        dong_list = await self._get_dong_list(sigungu_code)
        if not dong_list:
            logger.warning("[증분] 동 목록 비어있음: %s %s", sido, sigungu)
            return self._stats.copy()

        logger.info("[증분] Phase 1: %d개 동에서 단지 목록 수집", len(dong_list))

        # 전체 단지 목록 수집
        all_complexes: List[Dict] = []
        for dong_info in dong_list:
            dong_code = dong_info.get("cortarNo", "")
            complexes = await self._get_complexes_in_dong(dong_code)
            all_complexes.extend(complexes)

        self._stats["complexes_found"] = len(all_complexes)
        logger.info("[증분] Phase 1 완료: 총 %d개 단지 발견", len(all_complexes))

        # Phase 2: 세대수 필터 비활성화 (API에서 세대수 미제공)
        filtered = all_complexes
        logger.info("[증분] Phase 2: 필터 없이 %d개 전체 대상", len(filtered))

        if not filtered:
            return self._stats.copy()

        # Phase 3 & 4: DB 비교 후 증분 크롤링
        db = SessionLocal()
        try:
            # 단지번호별 dealCnt 맵
            complex_deal_map: Dict[str, int] = {}
            for c in filtered:
                cno = str(c.get("complexNo", ""))
                deal_cnt = c.get("dealCnt", 0)
                try:
                    deal_cnt = int(deal_cnt) if deal_cnt else 0
                except (ValueError, TypeError):
                    deal_cnt = 0
                complex_deal_map[cno] = deal_cnt

            all_complex_nos = list(complex_deal_map.keys())

            # Phase 3: dealCnt=0 단지 일괄 비활성화
            zero_deal_nos = [cno for cno, cnt in complex_deal_map.items() if cnt == 0]
            if zero_deal_nos:
                deactivated = self._bulk_deactivate_listings(db, zero_deal_nos)
                logger.info(
                    "[증분] Phase 3: dealCnt=0 → %d개 단지, %d개 매물 비활성화",
                    len(zero_deal_nos), deactivated,
                )

            # Phase 4: dealCnt 변화 감지
            nonzero_nos = [cno for cno, cnt in complex_deal_map.items() if cnt > 0]
            db_counts = self._get_active_listing_counts(db, nonzero_nos)

            # 크롤링 대상: DB에 없거나, dealCnt != DB 활성 매물 수
            crawl_targets = []
            skipped_same = 0
            for cno in nonzero_nos:
                api_deal_cnt = complex_deal_map[cno]
                db_active_cnt = db_counts.get(cno, -1)  # -1 = DB에 없음

                if api_deal_cnt == db_active_cnt:
                    skipped_same += 1
                    continue
                crawl_targets.append(cno)

            logger.info(
                "[증분] Phase 4: dealCnt 동일 %d개 스킵, %d개 상세 크롤링 대상",
                skipped_same, len(crawl_targets),
            )

            # 대상 단지만 상세 크롤링
            # 단지번호 → 단지 데이터 맵 생성
            complex_data_map = {str(c.get("complexNo", "")): c for c in filtered}

            for cno in crawl_targets:
                complex_data = complex_data_map.get(cno)
                if not complex_data:
                    continue
                try:
                    await self.crawl_complex(db, complex_data, sido, sigungu)
                except Exception as e:
                    self._stats["errors"] += 1
                    logger.error(
                        "[증분] 단지 크롤링 실패 (%s): %s",
                        complex_data.get("complexName", "?"), str(e),
                        exc_info=True,
                    )

            db.commit()
            logger.info(
                "===== [증분] 크롤링 완료: %s %s =====\n"
                "  전체 단지: %d, 세대수 필터: -%d, dealCnt=0: -%d, 변화 없음: -%d\n"
                "  실제 크롤링: %d개 단지, 매물 발견: %d, 저장: %d, 에러: %d",
                sido, sigungu,
                len(all_complexes), skipped_small, len(zero_deal_nos), skipped_same,
                len(crawl_targets),
                self._stats["articles_found"],
                self._stats["articles_saved"],
                self._stats["errors"],
            )

        except Exception as e:
            db.rollback()
            logger.error("[증분] 치명적 에러: %s", str(e), exc_info=True)
            raise
        finally:
            db.close()

        return self._stats.copy()

    async def crawl_all_target_regions_incremental(self) -> List[Dict]:
        """설정된 모든 대상 지역을 증분 크롤링.

        Returns:
            지역별 크롤링 통계 리스트
        """
        results = []

        if not self.target_regions:
            logger.warning("[증분] 크롤링 대상 지역이 설정되지 않음")
            return results

        logger.info("[증분] 전체 증분 크롤링 시작: %d개 지역", len(self.target_regions))

        for region in self.target_regions:
            sido = region.get("sido", "")
            sigungu = region.get("sigungu", "")

            if not sido or not sigungu:
                logger.warning("[증분] 잘못된 지역 설정: %s", region)
                continue

            try:
                stats = await self.crawl_region_incremental(sido, sigungu)
                results.append({"sido": sido, "sigungu": sigungu, **stats})
            except Exception as e:
                logger.error("[증분] 지역 크롤링 실패 (%s %s): %s", sido, sigungu, str(e))
                results.append({"sido": sido, "sigungu": sigungu, "error": str(e)})

        logger.info("[증분] 전체 증분 크롤링 완료: %d개 지역 처리", len(results))
        return results
