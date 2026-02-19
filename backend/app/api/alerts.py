"""
급매 알림 API

KB시세 대비 할인율이 높은 단지를 조회합니다.
- GET /api/alerts/bargains : 급매 알림 목록 (할인율/시간 필터 지원)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models.database import get_db
from app.models.apartment import ApartmentComplex, ComplexComparison

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ── 응답 스키마 ──────────────────────────────────────────
class BargainItem(BaseModel):
    """급매 단지 항목"""
    complex_name: str
    sigungu: str
    dong: Optional[str]
    area_sqm: float
    discount_rate: float
    kb_price: Optional[int]
    recent_deal_price: Optional[int]
    compared_at: Optional[datetime]

    class Config:
        orm_mode = True


class BargainResponse(BaseModel):
    """급매 알림 응답"""
    total: int
    threshold: float
    since_hours: int
    items: List[BargainItem]


# ── 급매 알림 엔드포인트 ─────────────────────────────────
@router.get("/bargains", response_model=BargainResponse)
def get_bargain_alerts(
    min_discount: float = Query(5.0, description="최소 할인율 (%)"),
    since_hours: int = Query(24, description="최근 N시간 이내 비교 데이터"),
    limit: int = Query(20, ge=1, le=100, description="최대 조회 건수"),
    db: Session = Depends(get_db),
):
    """KB시세 대비 할인율이 높은 급매 단지를 반환합니다.

    - min_discount: 최소 할인율 기준 (기본 5%)
    - since_hours: 최근 비교 시점 기준 시간 (기본 24시간)
    - limit: 최대 반환 건수
    """
    # 시간 기준 계산
    cutoff = datetime.utcnow() - timedelta(hours=since_hours)

    # ComplexComparison JOIN ApartmentComplex — 할인율 + 시간 필터
    query = (
        db.query(ComplexComparison, ApartmentComplex)
        .join(ApartmentComplex, ComplexComparison.complex_id == ApartmentComplex.id)
        .filter(ComplexComparison.deal_discount_rate > min_discount)
        .filter(ComplexComparison.compared_at >= cutoff)
        .order_by(desc(ComplexComparison.deal_discount_rate))
    )

    total = query.count()
    rows = query.limit(limit).all()

    # 응답 조립
    items = []
    for comp, cpx in rows:
        items.append(BargainItem(
            complex_name=cpx.name,
            sigungu=cpx.sigungu,
            dong=cpx.dong,
            area_sqm=comp.area_sqm,
            discount_rate=comp.deal_discount_rate,
            kb_price=comp.kb_price_mid,
            recent_deal_price=comp.recent_deal_price,
            compared_at=comp.compared_at,
        ))

    return BargainResponse(
        total=total,
        threshold=min_discount,
        since_hours=since_hours,
        items=items,
    )
