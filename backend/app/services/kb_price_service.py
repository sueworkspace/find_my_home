"""
KB시세 수집 및 DB 저장 서비스

네이버 부동산에서 수집한 아파트 단지 정보를 기반으로
KB부동산에서 단지별 KB시세를 조회하고 DB에 저장합니다.

주요 기능:
- ApartmentComplex 테이블의 단지들에 대해 KB시세 조회
- KB시세(면적별 하한가/일반가/상한가)를 KBPrice 테이블에 upsert
- 배치 처리: 전체 또는 특정 지역 단지 일괄 처리
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.crawler.kb_price_client import KBPriceClient
from app.models.apartment import ApartmentComplex, KBPrice
from app.models.database import SessionLocal

logger = logging.getLogger(__name__)


class KBPriceService:
    """KB시세 수집/저장 서비스.

    사용법:
        service = KBPriceService()
        stats = await service.update_kb_prices_for_region("서울특별시", "강남구")
        await service.close()

    또는 단일 단지:
        hcpc_no, count = await service.update_prices_for_complex(db, complex_obj)
    """

    def __init__(self):
        self._client = KBPriceClient()
        self._stats: Dict[str, int] = {}
        self._reset_stats()

    async def close(self):
        """리소스 정리."""
        await self._client.close()

    def _reset_stats(self):
        """통계 카운터 초기화."""
        self._stats = {
            "total_complexes": 0,      # 대상 단지 수
            "matched_complexes": 0,    # KB 매칭 성공 단지 수
            "prices_saved": 0,         # 저장/갱신된 시세 항목 수
            "match_failures": 0,       # KB 매칭 실패 단지 수
            "price_fetch_failures": 0, # 시세 조회 실패 수
            "errors": 0,              # 기타 에러 수
        }

    # ──────────────────────────────────────────
    # 단일 단지 KB시세 처리
    # ──────────────────────────────────────────

    async def update_prices_for_complex(
        self,
        db: Session,
        complex_obj: ApartmentComplex,
    ) -> Tuple[Optional[str], int]:
        """단일 아파트 단지의 KB시세를 조회하여 DB에 저장.

        Args:
            db: SQLAlchemy 세션
            complex_obj: ApartmentComplex 모델 객체

        Returns:
            (kb_hcpc_no, saved_count) 튜플
            - kb_hcpc_no: 매칭된 KB 단지 코드 (실패 시 None)
            - saved_count: 저장된 시세 항목 수
        """
        complex_name = complex_obj.name
        sido = complex_obj.sido
        sigungu = complex_obj.sigungu
        dong = complex_obj.dong

        logger.info(
            "KB시세 조회 시작: [%d] %s (%s %s %s)",
            complex_obj.id, complex_name, sido, sigungu, dong or "",
        )

        # 1) KB 단지 매칭 및 시세 조회
        # dong_code가 있으면 직접 사용 (DONG_LAWDCD_MAP 불필요)
        dong_code = getattr(complex_obj, 'dong_code', None)
        hcpc_no, prices = await self._client.get_prices_for_complex(
            complex_name=complex_name,
            sido=sido,
            sigungu=sigungu,
            dong=dong,
            dong_code=dong_code,
        )

        if hcpc_no is None:
            logger.warning(
                "KB 단지 매칭 실패: [%d] %s", complex_obj.id, complex_name,
            )
            self._stats["match_failures"] += 1
            return None, 0

        self._stats["matched_complexes"] += 1

        if not prices:
            logger.warning(
                "KB시세 데이터 없음: [%d] %s (hcpcNo=%s)",
                complex_obj.id, complex_name, hcpc_no,
            )
            self._stats["price_fetch_failures"] += 1
            return hcpc_no, 0

        # 2) DB에 시세 upsert
        saved_count = _upsert_kb_prices(db, complex_obj.id, prices)
        self._stats["prices_saved"] += saved_count

        logger.info(
            "KB시세 저장 완료: [%d] %s - %d개 면적 항목 (hcpcNo=%s)",
            complex_obj.id, complex_name, saved_count, hcpc_no,
        )

        return hcpc_no, saved_count

    # ──────────────────────────────────────────
    # 지역별 배치 처리
    # ──────────────────────────────────────────

    async def update_kb_prices_for_region(
        self,
        sido: str,
        sigungu: str,
    ) -> Dict[str, int]:
        """특정 시/도, 시/군/구의 모든 단지에 대해 KB시세 일괄 조회/저장.

        ApartmentComplex 테이블에서 해당 지역의 단지를 조회하고,
        각 단지에 대해 KB시세를 수집합니다.

        Args:
            sido: 시/도 이름 (예: "서울특별시")
            sigungu: 시/군/구 이름 (예: "강남구")

        Returns:
            처리 통계 dict
        """
        logger.info("===== KB시세 수집 시작: %s %s =====", sido, sigungu)
        self._reset_stats()

        db = SessionLocal()
        try:
            # 해당 지역의 아파트 단지 조회
            complexes = db.query(ApartmentComplex).filter(
                ApartmentComplex.sido == sido,
                ApartmentComplex.sigungu == sigungu,
            ).all()

            if not complexes:
                logger.warning(
                    "DB에 단지 데이터 없음: %s %s (실거래가 수집을 먼저 실행하세요)",
                    sido, sigungu,
                )
                return self._stats.copy()

            self._stats["total_complexes"] = len(complexes)
            logger.info(
                "%s %s: %d개 단지 KB시세 수집 시작",
                sido, sigungu, len(complexes),
            )

            # 각 단지에 대해 KB시세 조회 및 저장
            for i, complex_obj in enumerate(complexes, 1):
                try:
                    logger.info(
                        "진행: [%d/%d] %s",
                        i, len(complexes), complex_obj.name,
                    )
                    await self.update_prices_for_complex(db, complex_obj)
                except Exception as e:
                    self._stats["errors"] += 1
                    logger.error(
                        "KB시세 처리 실패 [%d] %s: %s",
                        complex_obj.id, complex_obj.name, str(e),
                        exc_info=True,
                    )

            # 모든 단지 처리 완료 후 커밋
            db.commit()

            logger.info(
                "===== KB시세 수집 완료: %s %s =====\n"
                "  전체 단지: %d개\n"
                "  매칭 성공: %d개\n"
                "  시세 저장: %d개 항목\n"
                "  매칭 실패: %d개\n"
                "  조회 실패: %d개\n"
                "  에러: %d건",
                sido, sigungu,
                self._stats["total_complexes"],
                self._stats["matched_complexes"],
                self._stats["prices_saved"],
                self._stats["match_failures"],
                self._stats["price_fetch_failures"],
                self._stats["errors"],
            )

        except Exception as e:
            db.rollback()
            logger.error(
                "KB시세 수집 중 치명적 에러: %s", str(e), exc_info=True,
            )
            raise
        finally:
            db.close()

        return self._stats.copy()

    async def update_kb_prices_for_all_regions(
        self,
        target_regions: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """여러 지역의 KB시세를 일괄 수집.

        Args:
            target_regions: 지역 리스트
                예: [{"sido": "서울특별시", "sigungu": "강남구"}, ...]

        Returns:
            지역별 처리 통계 리스트
        """
        results: List[Dict[str, Any]] = []

        if not target_regions:
            logger.warning("KB시세 수집 대상 지역이 비어있음")
            return results

        logger.info("KB시세 전체 수집 시작: %d개 지역", len(target_regions))

        for region in target_regions:
            sido = region.get("sido", "")
            sigungu = region.get("sigungu", "")

            if not sido or not sigungu:
                logger.warning("잘못된 지역 설정: %s", region)
                continue

            try:
                stats = await self.update_kb_prices_for_region(sido, sigungu)
                results.append({
                    "sido": sido,
                    "sigungu": sigungu,
                    **stats,
                })
            except Exception as e:
                logger.error(
                    "지역 KB시세 수집 실패 (%s %s): %s",
                    sido, sigungu, str(e),
                )
                results.append({
                    "sido": sido,
                    "sigungu": sigungu,
                    "error": str(e),
                })

        logger.info("KB시세 전체 수집 완료: %d개 지역 처리", len(results))
        return results

    # ──────────────────────────────────────────
    # 동 단위 병렬 수집 (고속 모드)
    # ──────────────────────────────────────────

    async def update_kb_prices_parallel(
        self,
        concurrency: int = 5,
    ) -> Dict[str, Any]:
        """동(dong_code) 단위 병렬 KB시세 수집 — 기존 대비 10~25배 빠름.

        기존 방식(단지별 순차):
          단지마다 get_complex_list 호출 → 16,037 × 1.5초 = 24시간 이상

        개선 방식(동 단위 배치 + 병렬):
          1) dong_code로 단지 그룹화 → get_complex_list는 동당 1번만 호출
          2) Semaphore(concurrency)로 N개 동 동시 처리

        Args:
            concurrency: 동시 처리할 동(dong) 수 (기본 5)

        Returns:
            전체 통계 dict
        """
        import time
        start = time.time()
        logger.info("===== KB시세 고속 수집 시작 (concurrency=%d) =====", concurrency)

        db = SessionLocal()
        try:
            # dong_code가 있는 단지만 대상 (없으면 KB API 조회 불가)
            complexes = (
                db.query(ApartmentComplex)
                .filter(ApartmentComplex.dong_code.isnot(None))
                .all()
            )

            if not complexes:
                logger.warning("dong_code가 설정된 단지 없음 — populate_dong_codes 먼저 실행 필요")
                return {"total_complexes": 0, "dong_groups": 0}

            # dong_code별로 그룹화
            dong_groups: Dict[str, List[ApartmentComplex]] = defaultdict(list)
            for c in complexes:
                dong_groups[c.dong_code].append(c)

            logger.info(
                "대상: %d개 단지 / %d개 동 그룹 (평균 %.1f개/동)",
                len(complexes),
                len(dong_groups),
                len(complexes) / max(len(dong_groups), 1),
            )

            # 각 동 그룹을 Semaphore로 병렬 처리
            semaphore = asyncio.Semaphore(concurrency)
            tasks = [
                self._process_dong_group(dong_code, group, semaphore, db)
                for dong_code, group in dong_groups.items()
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 통계 집계
            total_stats: Dict[str, int] = {
                "total_complexes": len(complexes),
                "dong_groups": len(dong_groups),
                "matched": 0,
                "saved": 0,
                "failed": 0,
                "errors": 0,
            }
            for r in results:
                if isinstance(r, Exception):
                    total_stats["errors"] += 1
                    logger.error("동 처리 예외: %s", str(r))
                elif isinstance(r, dict):
                    total_stats["matched"] += r.get("matched", 0)
                    total_stats["saved"] += r.get("saved", 0)
                    total_stats["failed"] += r.get("failed", 0)

            elapsed = time.time() - start
            logger.info(
                "===== KB시세 고속 수집 완료 =====\n"
                "  소요시간: %.1f초 (%.1f분)\n"
                "  처리 동 수: %d개\n"
                "  매칭 성공: %d개\n"
                "  시세 저장: %d개 항목\n"
                "  매칭 실패: %d개\n"
                "  에러: %d건",
                elapsed, elapsed / 60,
                len(dong_groups),
                total_stats["matched"],
                total_stats["saved"],
                total_stats["failed"],
                total_stats["errors"],
            )
            return total_stats

        finally:
            db.close()

    async def _process_dong_group(
        self,
        dong_code: str,
        complexes: List[ApartmentComplex],
        semaphore: asyncio.Semaphore,
        db: Session,
    ) -> Dict[str, int]:
        """하나의 dong_code에 속한 단지들의 KB시세를 배치 처리.

        get_complex_list를 1번만 호출하고, 결과를 해당 동의 모든 단지에 재사용.

        Args:
            dong_code: 법정동코드 10자리
            complexes: 해당 동의 ApartmentComplex 목록
            semaphore: 동시 처리 수 제한
            db: SQLAlchemy 세션

        Returns:
            {"matched": int, "saved": int, "failed": int}
        """
        async with semaphore:
            stats = {"matched": 0, "saved": 0, "failed": 0}

            # 1. 이 동의 KB 단지 목록 1번만 조회 (핵심 최적화)
            try:
                kb_list = await self._client.get_complex_list(dong_code)
            except Exception as e:
                logger.error("get_complex_list 실패 dong_code=%s: %s", dong_code, e)
                stats["failed"] = len(complexes)
                return stats

            if not kb_list:
                logger.debug("KB 단지 목록 없음: dong_code=%s", dong_code)
                stats["failed"] = len(complexes)
                return stats

            # 2. 각 DB 단지를 KB 목록에서 매칭 후 시세 조회
            for complex_obj in complexes:
                try:
                    matched = self._client.match_from_list(
                        complex_obj.name, kb_list, dong=complex_obj.dong,
                    )
                    if not matched:
                        stats["failed"] += 1
                        continue

                    kb_id = int(matched["단지기본일련번호"])
                    prices = await self._client.get_all_prices(kb_id)

                    if prices:
                        saved = _upsert_kb_prices(db, complex_obj.id, prices)
                        db.commit()
                        stats["matched"] += 1
                        stats["saved"] += saved
                    else:
                        stats["failed"] += 1

                except Exception as e:
                    db.rollback()
                    stats["failed"] += 1
                    logger.error(
                        "단지 처리 실패 [%d] %s: %s",
                        complex_obj.id, complex_obj.name, e,
                    )

            return stats


# ──────────────────────────────────────────
# DB 저장 헬퍼 함수 (모듈 레벨)
# ──────────────────────────────────────────

def _upsert_kb_prices(
    db: Session,
    complex_id: int,
    prices: List[Dict[str, Any]],
) -> int:
    """KB시세 데이터를 KBPrice 테이블에 upsert (insert or update).

    동일 단지+면적 조합이 이미 존재하면 가격을 갱신하고,
    없으면 새로 삽입합니다.

    Args:
        db: SQLAlchemy 세션
        complex_id: ApartmentComplex.id
        prices: 면적별 시세 리스트
            각 항목: {"area_sqm", "price_lower", "price_mid", "price_upper"}

    Returns:
        저장(insert + update)된 항목 수
    """
    saved_count = 0

    for price_data in prices:
        area_sqm = price_data.get("area_sqm")
        if area_sqm is None:
            continue

        price_lower = price_data.get("price_lower")
        price_mid = price_data.get("price_mid")
        price_upper = price_data.get("price_upper")

        # 기존 레코드 조회 (complex_id + area_sqm unique constraint)
        existing = db.query(KBPrice).filter(
            KBPrice.complex_id == complex_id,
            KBPrice.area_sqm == area_sqm,
        ).first()

        if existing:
            # 기존 시세 갱신 (가격이 동일해도 updated_at을 명시적으로 갱신해
            # SQLAlchemy가 반드시 UPDATE를 발행하도록 함)
            from datetime import datetime
            if price_lower is not None:
                existing.price_lower = price_lower
            if price_mid is not None:
                existing.price_mid = price_mid
            if price_upper is not None:
                existing.price_upper = price_upper
            existing.updated_at = datetime.now()
            logger.debug(
                "KB시세 갱신: complex_id=%d, area=%.2f, "
                "lower=%s, mid=%s, upper=%s",
                complex_id, area_sqm, price_lower, price_mid, price_upper,
            )
        else:
            # 신규 삽입
            new_price = KBPrice(
                complex_id=complex_id,
                area_sqm=area_sqm,
                price_lower=price_lower,
                price_mid=price_mid,
                price_upper=price_upper,
            )
            db.add(new_price)
            logger.debug(
                "KB시세 신규 삽입: complex_id=%d, area=%.2f, "
                "lower=%s, mid=%s, upper=%s",
                complex_id, area_sqm, price_lower, price_mid, price_upper,
            )

        saved_count += 1

    return saved_count


def get_kb_prices_for_complex(
    db: Session,
    complex_id: int,
) -> List[KBPrice]:
    """특정 단지의 모든 KB시세를 조회.

    Args:
        db: SQLAlchemy 세션
        complex_id: ApartmentComplex.id

    Returns:
        KBPrice 객체 리스트 (면적순 정렬)
    """
    return (
        db.query(KBPrice)
        .filter(KBPrice.complex_id == complex_id)
        .order_by(KBPrice.area_sqm)
        .all()
    )


def get_kb_price_by_area(
    db: Session,
    complex_id: int,
    area_sqm: float,
    tolerance: float = 1.0,
) -> Optional[KBPrice]:
    """특정 단지 + 면적에 해당하는 KB시세를 조회.

    정확한 면적 일치가 없을 경우, tolerance 범위 내에서 가장 가까운 면적의
    시세를 반환합니다. 네이버 매물의 면적과 KB시세 면적이 약간 다를 수
    있기 때문입니다.

    Args:
        db: SQLAlchemy 세션
        complex_id: ApartmentComplex.id
        area_sqm: 전용면적 (제곱미터)
        tolerance: 면적 허용 오차 (제곱미터, 기본 1.0)

    Returns:
        가장 근접한 KBPrice 객체, 없으면 None
    """
    # 1) 정확한 면적으로 먼저 조회
    exact = db.query(KBPrice).filter(
        KBPrice.complex_id == complex_id,
        KBPrice.area_sqm == area_sqm,
    ).first()

    if exact:
        return exact

    # 2) tolerance 범위 내에서 가장 가까운 면적 조회
    candidates = (
        db.query(KBPrice)
        .filter(
            KBPrice.complex_id == complex_id,
            KBPrice.area_sqm >= area_sqm - tolerance,
            KBPrice.area_sqm <= area_sqm + tolerance,
        )
        .all()
    )

    if not candidates:
        return None

    # 면적 차이가 가장 작은 후보 반환
    best = min(candidates, key=lambda p: abs(p.area_sqm - area_sqm))
    return best
