"""
단지별 KB시세 vs 실거래가 비교 서비스

ApartmentComplex 단위로 KB시세 중간값과 최근 실거래가를 비교하여
ComplexComparison 테이블을 갱신합니다.

할인율 = (KB시세 중간값 - 최근 실거래가) / KB시세 중간값 × 100
  양수 → 실거래가가 KB시세보다 낮음 (급매 가능성)
  음수 → 실거래가가 KB시세보다 높음
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.apartment import (
    ApartmentComplex,
    KBPrice,
    RealTransaction,
    ComplexComparison,
)

logger = logging.getLogger(__name__)

# 최근 거래로 인정하는 기간 (일)
RECENT_DEAL_DAYS = 90


def _get_recent_deal(
    db: Session,
    complex_id: int,
    area_sqm: float,
    area_tolerance: float = 3.0,
) -> Optional[Dict[str, Any]]:
    """특정 단지/면적의 최근 실거래가를 조회한다.

    Args:
        db: SQLAlchemy 세션
        complex_id: 단지 ID
        area_sqm: 전용면적 (m2)
        area_tolerance: 면적 오차 허용 범위 (m2, 기본 3.0)

    Returns:
        {'deal_price': int, 'deal_date': datetime, 'deal_count': int} 또는 None
    """
    cutoff = datetime.now() - timedelta(days=RECENT_DEAL_DAYS)

    # 면적 허용 오차 내 최근 거래 조회
    recent = (
        db.query(RealTransaction)
        .filter(
            RealTransaction.complex_id == complex_id,
            RealTransaction.area_sqm.between(
                area_sqm - area_tolerance, area_sqm + area_tolerance
            ),
            RealTransaction.deal_date >= cutoff,
        )
        .order_by(RealTransaction.deal_date.desc())
        .first()
    )

    if recent is None:
        return None

    # 3개월 거래 건수
    deal_count = (
        db.query(func.count(RealTransaction.id))
        .filter(
            RealTransaction.complex_id == complex_id,
            RealTransaction.area_sqm.between(
                area_sqm - area_tolerance, area_sqm + area_tolerance
            ),
            RealTransaction.deal_date >= cutoff,
        )
        .scalar()
        or 0
    )

    return {
        "deal_price": recent.deal_price,
        "deal_date": recent.deal_date,
        "deal_count": deal_count,
    }


def update_all_comparisons(db: Session) -> Dict[str, Any]:
    """모든 단지의 KB시세 vs 실거래가 비교를 갱신한다.

    KB시세가 존재하는 단지/면적 조합을 순회하며:
      1. 최근 실거래가 조회
      2. 할인율 계산
      3. ComplexComparison upsert

    Args:
        db: SQLAlchemy 세션

    Returns:
        {'updated': int, 'skipped': int} 요약
    """
    updated = 0
    skipped = 0

    # KB시세가 있는 모든 (complex_id, area_sqm) 조합 조회
    kb_rows = db.query(KBPrice).all()

    for kb in kb_rows:
        complex_id = kb.complex_id
        area_sqm = kb.area_sqm
        kb_mid = kb.price_mid

        if kb_mid is None:
            skipped += 1
            continue

        # 최근 실거래가 조회
        recent = _get_recent_deal(db, complex_id, area_sqm)

        if recent is None:
            skipped += 1
            continue

        deal_price = recent["deal_price"]
        deal_date = recent["deal_date"]
        deal_count = recent["deal_count"]

        # 할인율 계산 (양수 = 급매)
        discount_rate = (kb_mid - deal_price) / kb_mid * 100

        # ComplexComparison upsert
        existing = (
            db.query(ComplexComparison)
            .filter(
                ComplexComparison.complex_id == complex_id,
                ComplexComparison.area_sqm == area_sqm,
            )
            .first()
        )

        if existing:
            existing.kb_price_mid = kb_mid
            existing.recent_deal_price = deal_price
            existing.recent_deal_date = deal_date
            existing.deal_discount_rate = round(discount_rate, 2)
            existing.deal_count_3m = deal_count
        else:
            new_comp = ComplexComparison(
                complex_id=complex_id,
                area_sqm=area_sqm,
                kb_price_mid=kb_mid,
                recent_deal_price=deal_price,
                recent_deal_date=deal_date,
                deal_discount_rate=round(discount_rate, 2),
                deal_count_3m=deal_count,
            )
            db.add(new_comp)

        updated += 1

    db.commit()

    logger.info(
        "단지 비교 갱신 완료: %d건 업데이트, %d건 건너뜀",
        updated, skipped,
    )
    return {"updated": updated, "skipped": skipped}
