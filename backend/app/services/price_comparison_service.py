"""
가격 비교 엔진 서비스

네이버 부동산 매물 호가와 KB시세를 비교하여 할인율을 계산하고
PriceComparison 테이블에 저장합니다.

핵심 공식:
  할인율(%) = (KB시세 - 호가) / KB시세 × 100
  - 양수: 시세보다 저렴 (급매)
  - 음수: 시세보다 비쌈

매칭 기준:
  동일 단지(complex_id) + 유사 면적(±3m² 이내)
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.apartment import (
    ApartmentComplex,
    KBPrice,
    Listing,
    PriceComparison,
)

logger = logging.getLogger(__name__)

# 면적 매칭 허용 오차 (m²)
# 네이버 매물과 KB시세의 전용면적이 약간 다를 수 있음
AREA_TOLERANCE = 3.0


# ──────────────────────────────────────────
# KB시세 매칭 (DB 내부 매칭)
# ──────────────────────────────────────────

def _find_kb_price(
    db: Session,
    complex_id: int,
    area_sqm: float,
) -> Optional[KBPrice]:
    """매물의 단지+면적에 해당하는 KB시세를 DB에서 찾는다.

    매칭 전략:
      1. 정확히 일치하는 면적
      2. 허용 오차(±3m²) 내에서 가장 가까운 면적

    Args:
        db: SQLAlchemy 세션
        complex_id: 아파트 단지 ID (apartment_complex.id)
        area_sqm: 매물 전용면적 (m²)

    Returns:
        매칭된 KBPrice 객체, 없으면 None
    """
    # 1) 정확 매칭
    exact = db.query(KBPrice).filter(
        KBPrice.complex_id == complex_id,
        KBPrice.area_sqm == area_sqm,
    ).first()
    if exact:
        return exact

    # 2) 허용 오차 내 가장 가까운 면적
    candidates = (
        db.query(KBPrice)
        .filter(
            KBPrice.complex_id == complex_id,
            KBPrice.area_sqm >= area_sqm - AREA_TOLERANCE,
            KBPrice.area_sqm <= area_sqm + AREA_TOLERANCE,
        )
        .all()
    )
    if not candidates:
        return None

    # 면적 차이가 가장 작은 후보 반환
    return min(candidates, key=lambda p: abs(p.area_sqm - area_sqm))


# ──────────────────────────────────────────
# 단일 매물 비교
# ──────────────────────────────────────────

def compare_single_listing(
    db: Session,
    listing: Listing,
) -> Optional[PriceComparison]:
    """단일 매물에 대해 KB시세 비교를 수행한다.

    할인율 = (KB시세 - 호가) / KB시세 × 100

    Args:
        db: SQLAlchemy 세션
        listing: Listing 모델 객체

    Returns:
        생성/갱신된 PriceComparison 객체, KB시세 없으면 None
    """
    kb_price = _find_kb_price(db, listing.complex_id, listing.area_sqm)
    if not kb_price or not kb_price.price_mid:
        return None

    # 할인율 계산
    kb_mid = kb_price.price_mid
    asking = listing.asking_price
    price_diff = kb_mid - asking  # 양수 = 시세보다 저렴
    discount_rate = (price_diff / kb_mid) * 100

    # 기존 비교 결과 조회 (upsert: 이미 있으면 갱신)
    existing = db.query(PriceComparison).filter(
        PriceComparison.listing_id == listing.id,
    ).first()

    if existing:
        # 기존 결과 갱신
        existing.kb_price_id = kb_price.id
        existing.kb_mid_price = kb_mid
        existing.asking_price = asking
        existing.price_diff = price_diff
        existing.discount_rate = round(discount_rate, 2)
        return existing
    else:
        # 신규 생성
        comparison = PriceComparison(
            listing_id=listing.id,
            kb_price_id=kb_price.id,
            kb_mid_price=kb_mid,
            asking_price=asking,
            price_diff=price_diff,
            discount_rate=round(discount_rate, 2),
        )
        db.add(comparison)
        return comparison


# ──────────────────────────────────────────
# 지역별 전체 매물 일괄 비교
# ──────────────────────────────────────────

def compare_all_listings(
    db: Session,
    sido: str,
    sigungu: str,
) -> Dict[str, Any]:
    """지역 내 모든 활성 매물에 대해 KB시세 비교를 수행한다.

    PriceComparison 테이블에 결과를 upsert하고,
    처리 통계를 반환한다.

    Args:
        db: SQLAlchemy 세션
        sido: 시/도 (예: "서울특별시")
        sigungu: 시/군/구 (예: "강남구")

    Returns:
        비교 결과 통계 dict
    """
    logger.info("===== 가격 비교 시작: %s %s =====", sido, sigungu)

    # 해당 지역의 활성 매물 조회 (Listing + ApartmentComplex 조인)
    listings = (
        db.query(Listing)
        .join(ApartmentComplex, Listing.complex_id == ApartmentComplex.id)
        .filter(
            ApartmentComplex.sido == sido,
            ApartmentComplex.sigungu == sigungu,
            Listing.is_active == True,  # noqa: E712
        )
        .all()
    )

    stats = {
        "total_listings": len(listings),
        "compared": 0,         # KB시세 매칭 성공
        "no_kb_price": 0,      # KB시세 없음
        "bargains": 0,         # 시세보다 저렴한 매물 (할인율 > 0)
        "max_discount": 0.0,   # 최대 할인율
    }

    if not listings:
        logger.warning("활성 매물 없음: %s %s", sido, sigungu)
        return stats

    logger.info(
        "%s %s: %d개 매물 가격 비교 시작", sido, sigungu, len(listings),
    )

    for listing in listings:
        result = compare_single_listing(db, listing)
        if result:
            stats["compared"] += 1
            if result.discount_rate > 0:
                stats["bargains"] += 1
            if result.discount_rate > stats["max_discount"]:
                stats["max_discount"] = round(result.discount_rate, 2)
        else:
            stats["no_kb_price"] += 1

    # 일괄 커밋
    db.commit()

    logger.info(
        "===== 가격 비교 완료: %s %s =====\n"
        "  전체 매물: %d개\n"
        "  비교 성공: %d개\n"
        "  KB시세 없음: %d개\n"
        "  급매(시세 이하): %d개\n"
        "  최대 할인율: %.1f%%",
        sido, sigungu,
        stats["total_listings"],
        stats["compared"],
        stats["no_kb_price"],
        stats["bargains"],
        stats["max_discount"],
    )

    return stats


# ──────────────────────────────────────────
# 비교 결과 요약 통계 조회
# ──────────────────────────────────────────

def get_comparison_summary(
    db: Session,
    sido: str,
    sigungu: str,
) -> Dict[str, Any]:
    """지역의 가격 비교 요약 통계를 반환한다.

    Args:
        db: SQLAlchemy 세션
        sido: 시/도
        sigungu: 시/군/구

    Returns:
        요약 통계 dict (총 비교건수, 급매건수, 평균/최대 할인율)
    """
    # 활성 매물 + PriceComparison 조인하여 통계 조회
    result = (
        db.query(
            func.count(PriceComparison.id).label("total"),
            func.avg(PriceComparison.discount_rate).label("avg_discount"),
            func.max(PriceComparison.discount_rate).label("max_discount"),
            func.min(PriceComparison.discount_rate).label("min_discount"),
            # 급매 건수 (할인율 > 0인 매물)
            func.sum(
                case(
                    (PriceComparison.discount_rate > 0, 1),
                    else_=0,
                )
            ).label("bargain_count"),
        )
        .join(Listing, PriceComparison.listing_id == Listing.id)
        .join(ApartmentComplex, Listing.complex_id == ApartmentComplex.id)
        .filter(
            ApartmentComplex.sido == sido,
            ApartmentComplex.sigungu == sigungu,
            Listing.is_active == True,  # noqa: E712
        )
        .first()
    )

    if not result or result.total == 0:
        return {
            "total_compared": 0,
            "bargain_count": 0,
            "avg_discount_rate": None,
            "max_discount_rate": None,
            "min_discount_rate": None,
        }

    return {
        "total_compared": result.total,
        "bargain_count": int(result.bargain_count or 0),
        "avg_discount_rate": (
            round(float(result.avg_discount), 2)
            if result.avg_discount else None
        ),
        "max_discount_rate": (
            round(float(result.max_discount), 2)
            if result.max_discount else None
        ),
        "min_discount_rate": (
            round(float(result.min_discount), 2)
            if result.min_discount else None
        ),
    }


# ──────────────────────────────────────────
# 상위 급매 목록 조회
# ──────────────────────────────────────────

def get_top_bargains(
    db: Session,
    sido: str,
    sigungu: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """지역 내 할인율이 높은 급매물 TOP N을 조회한다.

    Args:
        db: SQLAlchemy 세션
        sido: 시/도
        sigungu: 시/군/구
        limit: 상위 N개 (기본 10)

    Returns:
        급매 리스트 (할인율 내림차순)
    """
    rows = (
        db.query(
            ApartmentComplex.name.label("apartment_name"),
            Listing.dong,
            Listing.area_sqm,
            Listing.floor,
            Listing.asking_price,
            PriceComparison.kb_mid_price,
            PriceComparison.discount_rate,
            PriceComparison.price_diff,
            Listing.listing_url,
        )
        .join(Listing, PriceComparison.listing_id == Listing.id)
        .join(ApartmentComplex, Listing.complex_id == ApartmentComplex.id)
        .filter(
            ApartmentComplex.sido == sido,
            ApartmentComplex.sigungu == sigungu,
            Listing.is_active == True,  # noqa: E712
            PriceComparison.discount_rate > 0,  # 시세보다 저렴한 것만
        )
        .order_by(PriceComparison.discount_rate.desc())
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        results.append({
            "apartment_name": row.apartment_name,
            "dong": row.dong,
            "area_sqm": round(row.area_sqm, 2),
            "floor": row.floor,
            "asking_price": row.asking_price,
            "kb_mid_price": row.kb_mid_price,
            "discount_rate": round(row.discount_rate, 2),
            "price_diff": row.price_diff,
            "listing_url": row.listing_url,
        })

    return results
