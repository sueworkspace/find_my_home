"""
실거래가 API 엔드포인트

- GET /api/transactions         : 특정 단지의 최근 실거래가 조회
- GET /api/transactions/summary : 특정 단지의 실거래가 요약 통계
- POST /api/transactions/collect: 특정 지역/기간의 실거래가 수집 실행
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.apartment import ApartmentComplex
from app.services.real_transaction_service import (
    collect_and_save,
    get_transactions_by_complex,
    get_transaction_summary,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


# ──────────────────────────────────────────
# 응답 스키마
# ──────────────────────────────────────────

class TransactionItem(BaseModel):
    """실거래가 개별 항목"""
    id: int
    apartment_name: str = Field(..., description="아파트명")
    area_sqm: float = Field(..., description="전용면적(m2)")
    floor: Optional[int] = Field(None, description="층")
    deal_price: int = Field(..., description="거래금액(만원)")
    deal_date: Optional[str] = Field(None, description="거래일자 (ISO 형식)")

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """실거래가 목록 응답"""
    complex_id: int = Field(..., description="아파트 단지 ID")
    complex_name: str = Field(..., description="아파트 단지명")
    items: List[TransactionItem]
    count: int = Field(..., description="조회된 건수")


class TransactionSummaryResponse(BaseModel):
    """실거래가 요약 통계 응답"""
    complex_id: int = Field(..., description="아파트 단지 ID")
    complex_name: str = Field(..., description="아파트 단지명")
    total_count: int = Field(..., description="총 거래 건수")
    max_price: Optional[int] = Field(None, description="최고 거래가(만원)")
    min_price: Optional[int] = Field(None, description="최저 거래가(만원)")
    avg_price: Optional[int] = Field(None, description="평균 거래가(만원)")
    latest_price: Optional[int] = Field(None, description="최근 거래가(만원)")
    latest_date: Optional[str] = Field(None, description="최근 거래일")


class CollectRequest(BaseModel):
    """실거래가 수집 요청"""
    sido: str = Field(..., description="시/도 (예: 서울특별시)")
    sigungu: str = Field(..., description="시/군/구 (예: 강남구)")
    deal_ymd: str = Field(
        ...,
        description="계약년월 6자리 (예: 202401)",
        min_length=6,
        max_length=6,
    )


class CollectResponse(BaseModel):
    """실거래가 수집 결과 응답"""
    sido: str
    sigungu: str
    deal_ymd: str
    fetched: int = Field(..., description="API에서 수집한 건수")
    saved: int = Field(..., description="DB에 저장한 건수")
    duplicates: int = Field(..., description="중복으로 건너뛴 건수")
    unmatched: int = Field(..., description="단지 매칭 실패 건수")


# ──────────────────────────────────────────
# API 엔드포인트
# ──────────────────────────────────────────

@router.get(
    "",
    response_model=TransactionListResponse,
    summary="특정 단지의 최근 실거래가 조회",
)
def get_transactions(
    complex_id: int = Query(..., description="아파트 단지 ID"),
    limit: int = Query(20, ge=1, le=100, description="최대 조회 건수"),
    area_sqm: Optional[float] = Query(
        None, description="전용면적 필터(m2)",
    ),
    db: Session = Depends(get_db),
):
    """
    특정 아파트 단지의 최근 실거래가 목록을 반환합니다.

    - 최근 거래일 순으로 정렬
    - 전용면적으로 필터링 가능
    """
    # 단지 존재 여부 확인
    cpx = db.query(ApartmentComplex).filter(
        ApartmentComplex.id == complex_id,
    ).first()
    if cpx is None:
        raise HTTPException(
            status_code=404,
            detail=f"단지를 찾을 수 없습니다: complex_id={complex_id}",
        )

    items = get_transactions_by_complex(
        db, complex_id=complex_id, limit=limit, area_sqm=area_sqm,
    )

    return TransactionListResponse(
        complex_id=complex_id,
        complex_name=cpx.name,
        items=[TransactionItem(**item) for item in items],
        count=len(items),
    )


@router.get(
    "/summary",
    response_model=TransactionSummaryResponse,
    summary="특정 단지의 실거래가 요약 통계",
)
def get_summary(
    complex_id: int = Query(..., description="아파트 단지 ID"),
    area_sqm: Optional[float] = Query(
        None, description="전용면적 필터(m2)",
    ),
    db: Session = Depends(get_db),
):
    """
    특정 아파트 단지의 실거래가 요약 통계를 반환합니다.

    - 총 거래 건수, 최고가, 최저가, 평균가, 최근 거래가
    """
    # 단지 존재 여부 확인
    cpx = db.query(ApartmentComplex).filter(
        ApartmentComplex.id == complex_id,
    ).first()
    if cpx is None:
        raise HTTPException(
            status_code=404,
            detail=f"단지를 찾을 수 없습니다: complex_id={complex_id}",
        )

    summary = get_transaction_summary(
        db, complex_id=complex_id, area_sqm=area_sqm,
    )
    if summary is None:
        raise HTTPException(
            status_code=404,
            detail=f"실거래가 데이터가 없습니다: complex_id={complex_id}",
        )

    return TransactionSummaryResponse(
        complex_id=complex_id,
        complex_name=cpx.name,
        **summary,
    )


@router.post(
    "/collect",
    response_model=CollectResponse,
    summary="실거래가 수집 실행",
)
async def collect_transactions(
    request: CollectRequest,
    db: Session = Depends(get_db),
):
    """
    지정된 지역과 기간의 국토교통부 아파트매매 실거래가를 수집하여 DB에 저장합니다.

    - 공공데이터포털 API를 호출하여 실거래가 데이터 수집
    - DB에 등록된 아파트 단지와 이름 기반 매칭
    - 중복 데이터는 자동으로 건너뜀

    주의:
    - 공공데이터포털 일일 트래픽 제한 (1,000건)이 있으므로 과도한 호출에 주의
    - DATA_GO_KR_API_KEY가 .env에 설정되어 있어야 함
    """
    # deal_ymd 유효성 검사
    try:
        year = int(request.deal_ymd[:4])
        month = int(request.deal_ymd[4:6])
        if not (2006 <= year <= 2030 and 1 <= month <= 12):
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=400,
            detail=(
                f"잘못된 계약년월 형식: {request.deal_ymd}. "
                "YYYYMM 형식이어야 합니다 (예: 202401)."
            ),
        )

    result = await collect_and_save(
        db,
        sido=request.sido,
        sigungu=request.sigungu,
        deal_ymd=request.deal_ymd,
    )

    return CollectResponse(**result)
