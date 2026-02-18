"""대시보드 API 라우터

크롤링 현황, 스케줄러 상태, 지역별 통계를 제공합니다.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.apartment import (
    ApartmentComplex, Listing, KBPrice, PriceComparison, RealTransaction,
)
from app.schemas.dashboard import (
    DBSummaryResponse,
    SchedulerStatusResponse,
    SchedulerJobInfo,
    RegionBreakdownResponse,
    RegionStatItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DBSummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    """DB 요약 통계를 반환합니다."""
    total_complexes = db.query(func.count(ApartmentComplex.id)).scalar() or 0
    active_listings = db.query(func.count(Listing.id)).filter(
        Listing.is_active == True  # noqa: E712
    ).scalar() or 0
    inactive_listings = db.query(func.count(Listing.id)).filter(
        Listing.is_active == False  # noqa: E712
    ).scalar() or 0
    kb_prices_count = db.query(func.count(KBPrice.id)).scalar() or 0

    # 급매: 할인율 > 0 (호가가 KB시세보다 낮은 매물)
    bargains_count = db.query(func.count(PriceComparison.id)).filter(
        PriceComparison.discount_rate > 0
    ).scalar() or 0

    real_transactions_count = db.query(func.count(RealTransaction.id)).scalar() or 0

    # 최근 업데이트 시각
    last_listing_update = db.query(func.max(Listing.updated_at)).scalar()
    last_kb_update = db.query(func.max(KBPrice.updated_at)).scalar()

    return DBSummaryResponse(
        total_complexes=total_complexes,
        active_listings=active_listings,
        inactive_listings=inactive_listings,
        kb_prices_count=kb_prices_count,
        bargains_count=bargains_count,
        real_transactions_count=real_transactions_count,
        last_listing_update=last_listing_update,
        last_kb_update=last_kb_update,
    )


@router.get("/scheduler", response_model=SchedulerStatusResponse)
def get_scheduler_status():
    """스케줄러 상태를 반환합니다."""
    from app.crawler.scheduler import get_scheduler

    scheduler = get_scheduler()

    if not scheduler or not scheduler.running:
        return SchedulerStatusResponse(is_running=False, jobs=[])

    jobs = []
    for job in scheduler.get_jobs():
        next_run = None
        if job.next_run_time:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")

        jobs.append(SchedulerJobInfo(
            job_id=job.id,
            name=job.name,
            trigger=str(job.trigger),
            next_run_time=next_run,
            is_paused=(job.next_run_time is None),
        ))

    return SchedulerStatusResponse(is_running=True, jobs=jobs)


@router.get("/regions", response_model=RegionBreakdownResponse)
def get_region_breakdown(db: Session = Depends(get_db)):
    """지역별 통계를 반환합니다."""

    # 지역별 단지 수
    complex_stats = (
        db.query(
            ApartmentComplex.sido,
            ApartmentComplex.sigungu,
            func.count(ApartmentComplex.id).label("complex_count"),
            func.max(ApartmentComplex.updated_at).label("latest_update"),
        )
        .group_by(ApartmentComplex.sido, ApartmentComplex.sigungu)
        .all()
    )

    items = []
    for row in complex_stats:
        sido = row.sido
        sigungu = row.sigungu

        # 해당 지역 단지 ID 목록 (서브쿼리 - select() 명시)
        complex_ids_q = select(ApartmentComplex.id).where(
            ApartmentComplex.sido == sido, ApartmentComplex.sigungu == sigungu
        )

        # 활성 매물 수
        active_count = db.query(func.count(Listing.id)).filter(
            Listing.complex_id.in_(complex_ids_q),
            Listing.is_active == True,  # noqa: E712
        ).scalar() or 0

        # KB시세 건수
        kb_count = db.query(func.count(KBPrice.id)).filter(
            KBPrice.complex_id.in_(complex_ids_q),
        ).scalar() or 0

        # 급매 건수: PriceComparison에서 해당 지역 매물의 할인율 > 0
        listing_ids_q = select(Listing.id).where(
            Listing.complex_id.in_(complex_ids_q),
            Listing.is_active == True,  # noqa: E712
        )
        bargain_count = db.query(func.count(PriceComparison.id)).filter(
            PriceComparison.listing_id.in_(listing_ids_q),
            PriceComparison.discount_rate > 0,
        ).scalar() or 0

        items.append(RegionStatItem(
            sido=sido,
            sigungu=sigungu,
            complex_count=row.complex_count,
            active_listing_count=active_count,
            kb_price_count=kb_count,
            bargain_count=bargain_count,
            latest_update=row.latest_update,
        ))

    # 시/도 → 시/군/구 순 정렬
    items.sort(key=lambda x: (x.sido, x.sigungu))

    return RegionBreakdownResponse(
        total_regions=len(items),
        items=items,
    )
