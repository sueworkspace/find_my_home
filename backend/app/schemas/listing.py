from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RegionResponse(BaseModel):
    """시/도 또는 시/군/구 목록 응답"""
    regions: List[str]


class ListingItem(BaseModel):
    """매물 리스트 개별 항목"""
    id: int
    apartment_name: str = Field(..., description="아파트명")
    dong: Optional[str] = Field(None, description="동")
    area_sqm: float = Field(..., description="전용면적(m2)")
    area_pyeong: float = Field(..., description="전용면적(평)")
    floor: Optional[int] = Field(None, description="층수")
    asking_price: int = Field(..., description="호가(만원)")
    kb_price: Optional[int] = Field(None, description="KB시세(만원)")
    discount_rate: Optional[float] = Field(None, description="할인율(%)")
    price_diff: Optional[int] = Field(None, description="시세 대비 차액(만원)")
    registered_at: Optional[datetime] = Field(None, description="등록일")
    recent_deal_price: Optional[int] = Field(None, description="최근 실거래가(만원)")
    recent_deal_date: Optional[datetime] = Field(None, description="최근 실거래일")
    listing_url: Optional[str] = Field(None, description="네이버 부동산 매물 URL")

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    """페이지네이션 메타 정보"""
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지당 항목 수")
    total_count: int = Field(..., description="전체 항목 수")
    total_pages: int = Field(..., description="전체 페이지 수")


class ListingListResponse(BaseModel):
    """매물 목록 응답"""
    items: List[ListingItem]
    pagination: PaginationMeta
