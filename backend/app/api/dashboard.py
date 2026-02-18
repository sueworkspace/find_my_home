"""대시보드 API 라우터

크롤링 현황, 스케줄러 상태, 지역별 통계를 제공합니다.
(네이버 매물 제거 후 KB시세 + 실거래가 + 단지비교 기반)
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.apartment import (
    ApartmentComplex, KBPrice, RealTransaction, ComplexComparison,
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
    kb_prices_count = db.query(func.count(KBPrice.id)).scalar() or 0
    real_transactions_count = db.query(func.count(RealTransaction.id)).scalar() or 0
    comparisons_count = db.query(func.count(ComplexComparison.id)).scalar() or 0

    # 급매: deal_discount_rate > 0 → 실거래가가 KB시세보다 낮게 거래된 단지/면적
    bargains_count = db.query(func.count(ComplexComparison.id)).filter(
        ComplexComparison.deal_discount_rate > 0
    ).scalar() or 0

    last_kb_update = db.query(func.max(KBPrice.updated_at)).scalar()
    last_transaction_update = db.query(func.max(RealTransaction.created_at)).scalar()

    return DBSummaryResponse(
        total_complexes=total_complexes,
        kb_prices_count=kb_prices_count,
        real_transactions_count=real_transactions_count,
        comparisons_count=comparisons_count,
        bargains_count=bargains_count,
        last_kb_update=last_kb_update,
        last_transaction_update=last_transaction_update,
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

        # 해당 지역 단지 ID 서브쿼리
        complex_ids_q = select(ApartmentComplex.id).where(
            ApartmentComplex.sido == sido, ApartmentComplex.sigungu == sigungu
        )

        # KB시세 건수
        kb_count = db.query(func.count(KBPrice.id)).filter(
            KBPrice.complex_id.in_(complex_ids_q),
        ).scalar() or 0

        # 실거래 건수
        deal_count = db.query(func.count(RealTransaction.id)).filter(
            RealTransaction.complex_id.in_(complex_ids_q),
        ).scalar() or 0

        # 단지 비교 건수
        comparison_count = db.query(func.count(ComplexComparison.id)).filter(
            ComplexComparison.complex_id.in_(complex_ids_q),
        ).scalar() or 0

        items.append(RegionStatItem(
            sido=sido,
            sigungu=sigungu,
            complex_count=row.complex_count,
            kb_price_count=kb_count,
            deal_count=deal_count,
            comparison_count=comparison_count,
            latest_update=row.latest_update,
        ))

    # 시/도 → 시/군/구 순 정렬
    items.sort(key=lambda x: (x.sido, x.sigungu))

    return RegionBreakdownResponse(
        total_regions=len(items),
        items=items,
    )
