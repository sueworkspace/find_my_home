"""지역 선택 API - 시/도, 시/군/구 목록 조회"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.apartment import ApartmentComplex
from app.schemas.listing import RegionResponse

router = APIRouter(prefix="/api/regions", tags=["regions"])


@router.get("/sido", response_model=RegionResponse, summary="시/도 목록 조회")
def get_sido_list(db: Session = Depends(get_db)):
    """
    DB에 등록된 아파트 단지 기준으로 시/도 목록을 반환합니다.
    """
    rows = (
        db.query(ApartmentComplex.sido)
        .distinct()
        .order_by(ApartmentComplex.sido)
        .all()
    )
    regions = [row[0] for row in rows]
    return RegionResponse(regions=regions)


@router.get("/sigungu", response_model=RegionResponse, summary="시/군/구 목록 조회")
def get_sigungu_list(
    sido: str = Query(..., description="시/도 이름 (예: 서울특별시)"),
    db: Session = Depends(get_db),
):
    """
    선택된 시/도에 속하는 시/군/구 목록을 반환합니다.
    """
    rows = (
        db.query(ApartmentComplex.sigungu)
        .filter(ApartmentComplex.sido == sido)
        .distinct()
        .order_by(ApartmentComplex.sigungu)
        .all()
    )
    regions = [row[0] for row in rows]
    return RegionResponse(regions=regions)
