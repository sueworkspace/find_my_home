"""대시보드 API 응답 스키마"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DBSummaryResponse(BaseModel):
    """DB 요약 통계 응답"""
    total_complexes: int = Field(..., description="전체 단지 수")
    kb_prices_count: int = Field(..., description="KB시세 건수")
    real_transactions_count: int = Field(..., description="실거래 건수")
    comparisons_count: int = Field(..., description="단지 비교 건수")
    bargains_count: int = Field(..., description="급매 건수 (실거래가 < KB시세)")
    last_kb_update: Optional[datetime] = Field(None, description="최근 KB시세 업데이트")
    last_transaction_update: Optional[datetime] = Field(None, description="최근 실거래가 업데이트")


class SchedulerJobInfo(BaseModel):
    """스케줄러 개별 잡 정보"""
    job_id: str = Field(..., description="잡 ID")
    name: str = Field(..., description="잡 이름")
    trigger: str = Field(..., description="트리거 유형")
    next_run_time: Optional[str] = Field(None, description="다음 실행 시각")
    is_paused: bool = Field(False, description="일시정지 여부")


class SchedulerStatusResponse(BaseModel):
    """스케줄러 상태 응답"""
    is_running: bool = Field(..., description="스케줄러 실행 중 여부")
    jobs: List[SchedulerJobInfo] = Field(default_factory=list)


class RegionStatItem(BaseModel):
    """지역별 통계 항목"""
    sido: str = Field(..., description="시/도")
    sigungu: str = Field(..., description="시/군/구")
    complex_count: int = Field(0, description="단지 수")
    kb_price_count: int = Field(0, description="KB시세 건수")
    deal_count: int = Field(0, description="실거래 건수")
    comparison_count: int = Field(0, description="단지 비교 건수")
    latest_update: Optional[datetime] = Field(None, description="최근 업데이트")


class RegionBreakdownResponse(BaseModel):
    """지역별 통계 응답"""
    total_regions: int = Field(..., description="전체 지역 수")
    items: List[RegionStatItem] = Field(default_factory=list)
