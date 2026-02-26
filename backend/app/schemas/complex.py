"""단지 목록 및 비교 스키마"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ComplexListItem(BaseModel):
    """단지 목록 항목 (KB시세 vs 실거래가 비교 포함)"""
    complex_id: int = Field(..., description="단지 ID")
    name: str = Field(..., description="아파트명")
    sido: str = Field(..., description="시/도")
    sigungu: str = Field(..., description="시/군/구")
    dong: Optional[str] = Field(None, description="법정동")
    built_year: Optional[int] = Field(None, description="건축년도")
    area_sqm: float = Field(..., description="전용면적 (m2)")
    kb_price_mid: int = Field(..., description="KB시세 중간값 (만원)")
    recent_deal_price: int = Field(..., description="최근 실거래가 (만원)")
    recent_deal_date: Optional[datetime] = Field(None, description="최근 실거래일")
    deal_discount_rate: float = Field(..., description="할인율 (양수=급매)")
    deal_count_3m: int = Field(0, description="최근 3개월 거래 건수")
    compared_at: Optional[datetime] = Field(None, description="비교 갱신 시각")

    class Config:
        from_attributes = True


class ComplexListResponse(BaseModel):
    """단지 목록 응답"""
    total: int = Field(..., description="전체 건수")
    items: List[ComplexListItem] = Field(default_factory=list)
