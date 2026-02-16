"""매물 리스트 API - 지역별 매물 조회 (필터/정렬/페이지네이션)"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, asc, func
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.apartment import (
    ApartmentComplex,
    Listing,
    KBPrice,
    PriceComparison,
    RealTransaction,
)
from app.schemas.listing import (
    ListingItem,
    ListingListResponse,
    PaginationMeta,
)

router = APIRouter(prefix="/api", tags=["listings"])

# m2 -> 평 변환 계수
SQM_TO_PYEONG = 0.3025


# 정렬 가능한 컬럼 매핑
SORT_COLUMN_MAP = {
    "apartment_name": ApartmentComplex.name,
    "area_sqm": Listing.area_sqm,
    "asking_price": Listing.asking_price,
    "kb_price": KBPrice.price_mid,
    "discount_rate": PriceComparison.discount_rate,
    "floor": Listing.floor,
    "registered_at": Listing.registered_at,
    "recent_deal_price": RealTransaction.deal_price,
}


@router.get(
    "/listings",
    response_model=ListingListResponse,
    summary="매물 목록 조회",
)
def get_listings(
    sido: str = Query(..., description="시/도 (예: 서울특별시)"),
    sigungu: str = Query(..., description="시/군/구 (예: 강남구)"),
    # 정렬
    sort_by: str = Query(
        "discount_rate",
        description="정렬 기준 (apartment_name, area_sqm, asking_price, kb_price, discount_rate, floor, registered_at, recent_deal_price)",
    ),
    order: str = Query(
        "desc",
        description="정렬 방향 (asc, desc)",
    ),
    # 필터
    min_discount: Optional[float] = Query(
        None, description="최소 할인율(%) (예: 5.0)"
    ),
    min_area: Optional[float] = Query(
        None, description="최소 전용면적(m2)"
    ),
    max_area: Optional[float] = Query(
        None, description="최대 전용면적(m2)"
    ),
    min_price: Optional[int] = Query(
        None, description="최소 호가(만원)"
    ),
    max_price: Optional[int] = Query(
        None, description="최대 호가(만원)"
    ),
    # 페이지네이션
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    size: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    db: Session = Depends(get_db),
):
    """
    선택된 시/도, 시/군/구 지역의 매물 목록을 반환합니다.

    - KB시세 대비 할인율, 최근 실거래가를 함께 반환
    - 정렬, 필터, 페이지네이션 지원
    """

    # -------------------------------------------------------
    # 최근 실거래가 서브쿼리: 단지+면적 기준 가장 최근 거래
    # -------------------------------------------------------
    latest_deal_subq = (
        db.query(
            RealTransaction.complex_id,
            RealTransaction.area_sqm,
            func.max(RealTransaction.deal_date).label("latest_deal_date"),
        )
        .group_by(RealTransaction.complex_id, RealTransaction.area_sqm)
        .subquery("latest_deal")
    )

    # -------------------------------------------------------
    # 메인 쿼리 조인
    # -------------------------------------------------------
    query = (
        db.query(
            Listing.id,
            ApartmentComplex.name.label("apartment_name"),
            Listing.dong,
            Listing.area_sqm,
            Listing.floor,
            Listing.asking_price,
            Listing.registered_at,
            Listing.listing_url,
            KBPrice.price_mid.label("kb_price"),
            PriceComparison.discount_rate,
            PriceComparison.price_diff,
            RealTransaction.deal_price.label("recent_deal_price"),
            RealTransaction.deal_date.label("recent_deal_date"),
        )
        .join(ApartmentComplex, Listing.complex_id == ApartmentComplex.id)
        # LEFT JOIN: KB시세가 없는 매물도 포함
        .outerjoin(
            KBPrice,
            (KBPrice.complex_id == ApartmentComplex.id)
            & (KBPrice.area_sqm == Listing.area_sqm),
        )
        # LEFT JOIN: 가격 비교가 없는 매물도 포함
        .outerjoin(
            PriceComparison,
            PriceComparison.listing_id == Listing.id,
        )
        # LEFT JOIN: 최근 실거래가
        .outerjoin(
            latest_deal_subq,
            (latest_deal_subq.c.complex_id == ApartmentComplex.id)
            & (latest_deal_subq.c.area_sqm == Listing.area_sqm),
        )
        .outerjoin(
            RealTransaction,
            (RealTransaction.complex_id == ApartmentComplex.id)
            & (RealTransaction.area_sqm == Listing.area_sqm)
            & (RealTransaction.deal_date == latest_deal_subq.c.latest_deal_date),
        )
    )

    # -------------------------------------------------------
    # 기본 필터: 지역 + 활성 매물만
    # -------------------------------------------------------
    query = query.filter(
        ApartmentComplex.sido == sido,
        ApartmentComplex.sigungu == sigungu,
        Listing.is_active == True,  # noqa: E712
    )

    # -------------------------------------------------------
    # 추가 필터
    # -------------------------------------------------------
    if min_discount is not None:
        query = query.filter(PriceComparison.discount_rate >= min_discount)

    if min_area is not None:
        query = query.filter(Listing.area_sqm >= min_area)

    if max_area is not None:
        query = query.filter(Listing.area_sqm <= max_area)

    if min_price is not None:
        query = query.filter(Listing.asking_price >= min_price)

    if max_price is not None:
        query = query.filter(Listing.asking_price <= max_price)

    # -------------------------------------------------------
    # 전체 카운트 (페이지네이션용)
    # -------------------------------------------------------
    total_count = query.count()
    total_pages = max(1, math.ceil(total_count / size))

    # -------------------------------------------------------
    # 정렬
    # -------------------------------------------------------
    sort_column = SORT_COLUMN_MAP.get(sort_by, PriceComparison.discount_rate)
    order_func = desc if order.lower() == "desc" else asc

    # NULL값은 정렬 시 마지막으로 밀기
    query = query.order_by(order_func(sort_column).nulls_last())

    # -------------------------------------------------------
    # 페이지네이션
    # -------------------------------------------------------
    offset = (page - 1) * size
    rows = query.offset(offset).limit(size).all()

    # -------------------------------------------------------
    # 응답 변환
    # -------------------------------------------------------
    items = []
    for row in rows:
        items.append(
            ListingItem(
                id=row.id,
                apartment_name=row.apartment_name,
                dong=row.dong,
                area_sqm=round(row.area_sqm, 2),
                area_pyeong=round(row.area_sqm * SQM_TO_PYEONG, 1),
                floor=row.floor,
                asking_price=row.asking_price,
                kb_price=row.kb_price,
                discount_rate=round(row.discount_rate, 2) if row.discount_rate is not None else None,
                price_diff=row.price_diff,
                registered_at=row.registered_at,
                recent_deal_price=row.recent_deal_price,
                recent_deal_date=row.recent_deal_date,
                listing_url=row.listing_url,
            )
        )

    return ListingListResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            size=size,
            total_count=total_count,
            total_pages=total_pages,
        ),
    )
