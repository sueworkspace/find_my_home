"""
가격 비교 API 엔드포인트

- POST /api/comparisons/run     : 지역별 가격 비교 실행
- GET  /api/comparisons/summary : 지역별 비교 결과 요약 통계
- GET  /api/comparisons/bargains: 지역별 상위 급매 목록
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.price_comparison_service import (
    compare_all_listings,
    get_comparison_summary,
    get_top_bargains,
)

router = APIRouter(prefix="/api/comparisons", tags=["comparisons"])


# ──────────────────────────────────────────
# 응답 스키마
# ──────────────────────────────────────────

class CompareRequest(BaseModel):
    """가격 비교 실행 요청"""
    sido: str = Field(..., description="시/도 (예: 서울특별시)")
    sigungu: str = Field(..., description="시/군/구 (예: 강남구)")


class CompareResponse(BaseModel):
    """가격 비교 실행 결과"""
    sido: str
    sigungu: str
    total_listings: int = Field(..., description="전체 매물 수")
    compared: int = Field(..., description="KB시세 매칭 성공 수")
    no_kb_price: int = Field(..., description="KB시세 없음 수")
    bargains: int = Field(..., description="급매(시세 이하) 수")
    max_discount: float = Field(..., description="최대 할인율(%)")


class SummaryResponse(BaseModel):
    """비교 결과 요약 통계"""
    sido: str
    sigungu: str
    total_compared: int = Field(..., description="총 비교 건수")
    bargain_count: int = Field(..., description="급매 건수")
    avg_discount_rate: Optional[float] = Field(None, description="평균 할인율(%)")
    max_discount_rate: Optional[float] = Field(None, description="최대 할인율(%)")
    min_discount_rate: Optional[float] = Field(None, description="최소 할인율(%)")


class BargainItem(BaseModel):
    """급매 항목"""
    apartment_name: str = Field(..., description="아파트명")
    dong: Optional[str] = Field(None, description="동")
    area_sqm: float = Field(..., description="전용면적(m²)")
    floor: Optional[int] = Field(None, description="층")
    asking_price: int = Field(..., description="호가(만원)")
    kb_mid_price: int = Field(..., description="KB시세(만원)")
    discount_rate: float = Field(..., description="할인율(%)")
    price_diff: int = Field(..., description="차액(만원)")
    listing_url: Optional[str] = Field(None, description="매물 URL")


class BargainListResponse(BaseModel):
    """급매 목록 응답"""
    sido: str
    sigungu: str
    items: List[BargainItem]
    count: int


# ──────────────────────────────────────────
# API 엔드포인트
# ──────────────────────────────────────────

@router.post(
    "/run",
    response_model=CompareResponse,
    summary="가격 비교 실행",
)
def run_comparison(
    request: CompareRequest,
    db: Session = Depends(get_db),
):
    """
    지정된 지역의 모든 활성 매물에 대해 KB시세 비교를 수행합니다.

    - Listing 테이블의 호가와 KBPrice 테이블의 KB시세를 매칭
    - 할인율 = (KB시세 - 호가) / KB시세 × 100
    - 결과를 PriceComparison 테이블에 저장

    사전 조건:
    - 네이버 크롤링으로 매물(Listing)이 수집되어 있어야 함
    - KB시세(KBPrice)가 수집되어 있어야 함
    """
    stats = compare_all_listings(db, request.sido, request.sigungu)
    return CompareResponse(
        sido=request.sido,
        sigungu=request.sigungu,
        **stats,
    )


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="비교 결과 요약 통계",
)
def get_summary(
    sido: str = Query(..., description="시/도"),
    sigungu: str = Query(..., description="시/군/구"),
    db: Session = Depends(get_db),
):
    """
    지역의 가격 비교 요약 통계를 반환합니다.

    - 총 비교 건수, 급매 건수, 평균/최대/최소 할인율
    """
    summary = get_comparison_summary(db, sido, sigungu)
    return SummaryResponse(
        sido=sido,
        sigungu=sigungu,
        **summary,
    )


@router.get(
    "/bargains",
    response_model=BargainListResponse,
    summary="상위 급매 목록",
)
def get_bargains(
    sido: str = Query(..., description="시/도"),
    sigungu: str = Query(..., description="시/군/구"),
    limit: int = Query(10, ge=1, le=50, description="조회 건수"),
    db: Session = Depends(get_db),
):
    """
    지역 내 할인율이 높은 급매물 TOP N을 반환합니다.

    - KB시세 대비 할인율 내림차순 정렬
    - 할인율 > 0인 매물만 (시세보다 저렴한 매물)
    """
    items = get_top_bargains(db, sido, sigungu, limit)
    return BargainListResponse(
        sido=sido,
        sigungu=sigungu,
        items=[BargainItem(**item) for item in items],
        count=len(items),
    )
