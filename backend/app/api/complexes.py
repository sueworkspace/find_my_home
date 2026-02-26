"""
단지 목록 API

KB시세 vs 실거래가 비교 데이터를 기반으로 단지 목록을 조회합니다.
- GET /api/complexes        : 단지 목록 (필터/정렬 지원)
- POST /api/complexes/compare : 비교 데이터 수동 갱신 (관리용)
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, asc
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db
from app.models.apartment import ApartmentComplex, ComplexComparison
from app.schemas.complex import ComplexListItem, ComplexListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/complexes", tags=["complexes"])


@router.get("", response_model=ComplexListResponse)
def list_complexes(
    sido: Optional[str] = Query(None, description="시/도 필터"),
    sigungu: Optional[str] = Query(None, description="시/군/구 필터"),
    name: Optional[str] = Query(None, description="단지명 검색 (부분 일치)"),
    min_discount: Optional[float] = Query(None, description="최소 할인율 (급매 필터, 예: 0)"),
    sort_by: str = Query("deal_discount_rate", description="정렬 기준: deal_discount_rate | kb_price_mid | recent_deal_price | deal_count_3m"),
    order: str = Query("desc", description="정렬 방향: desc | asc"),
    limit: int = Query(100, ge=1, le=500, description="최대 조회 건수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    db: Session = Depends(get_db),
):
    """KB시세 vs 실거래가 비교 단지 목록을 반환합니다.

    - KB시세와 실거래가가 모두 있는 단지/면적 조합만 조회
    - min_discount 파라미터로 급매(할인율 양수) 필터 가능
    - 정렬 기준과 방향 지정 가능
    """
    # ComplexComparison JOIN ApartmentComplex
    query = (
        db.query(ComplexComparison, ApartmentComplex)
        .join(ApartmentComplex, ComplexComparison.complex_id == ApartmentComplex.id)
    )

    # 지역 필터
    if sido:
        query = query.filter(ApartmentComplex.sido == sido)
    if sigungu:
        query = query.filter(ApartmentComplex.sigungu == sigungu)

    # 단지명 검색 필터 (ILIKE: 대소문자 무시 부분 일치)
    if name:
        query = query.filter(ApartmentComplex.name.ilike(f"%{name}%"))

    # 급매 필터
    if min_discount is not None:
        query = query.filter(ComplexComparison.deal_discount_rate >= min_discount)

    # 정렬
    sort_column_map = {
        "deal_discount_rate": ComplexComparison.deal_discount_rate,
        "kb_price_mid": ComplexComparison.kb_price_mid,
        "recent_deal_price": ComplexComparison.recent_deal_price,
        "deal_count_3m": ComplexComparison.deal_count_3m,
    }
    sort_col = sort_column_map.get(sort_by, ComplexComparison.deal_discount_rate)
    if order == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    total = query.count()
    rows = query.offset(offset).limit(limit).all()

    items = []
    for comp, cpx in rows:
        items.append(ComplexListItem(
            complex_id=cpx.id,
            name=cpx.name,
            sido=cpx.sido,
            sigungu=cpx.sigungu,
            dong=cpx.dong,
            built_year=cpx.built_year,
            area_sqm=comp.area_sqm,
            kb_price_mid=comp.kb_price_mid,
            recent_deal_price=comp.recent_deal_price,
            recent_deal_date=comp.recent_deal_date,
            deal_discount_rate=comp.deal_discount_rate,
            deal_count_3m=comp.deal_count_3m,
            compared_at=comp.compared_at,
        ))

    return ComplexListResponse(total=total, items=items)


@router.post("/compare", summary="단지 비교 데이터 수동 갱신")
def trigger_comparison(db: Session = Depends(get_db)):
    """KB시세 vs 실거래가 비교 데이터를 즉시 갱신합니다 (관리용)."""
    from app.services.complex_comparison_service import update_all_comparisons

    result = update_all_comparisons(db)
    return {"status": "ok", **result}
