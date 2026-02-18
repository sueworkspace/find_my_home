"""
APScheduler 기반 데이터 수집 파이프라인 스케줄러

수집 아키텍처:
  - KB시세 수집: 매일 KB_PRICE_CRON_HOUR시 (기본 06:00)
  - 실거래가 수집: 매일 02:00
  - 단지 비교(KB vs 실거래가) 업데이트: 매일 07:00 (KB시세 수집 후)
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings

logger = logging.getLogger(__name__)

# 전역 스케줄러 인스턴스
_scheduler: Optional[AsyncIOScheduler] = None


# ──────────────────────────────────────────
# 개별 작업 함수
# ──────────────────────────────────────────

async def run_kb_price_job() -> List[Dict[str, Any]]:
    """KB시세 수집 작업.

    DB에 등록된 아파트 단지에 대해 KB시세를 조회하여 저장합니다.
    """
    from app.services.kb_price_service import KBPriceService

    start_time = datetime.now()
    logger.info("===== KB시세 수집 시작: %s =====", start_time.isoformat())

    service = KBPriceService()
    try:
        results = await service.update_kb_prices_for_all_regions(
            settings.TARGET_REGIONS,
        )

        total_saved = sum(r.get("prices_saved", 0) for r in results)
        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info(
            "KB시세 수집 완료: %.1f초, %d개 지역, %d개 시세 저장",
            elapsed, len(results), total_saved,
        )
        return results

    except Exception as e:
        logger.error("KB시세 수집 실패: %s", str(e), exc_info=True)
        return []
    finally:
        await service.close()


async def run_real_transaction_job() -> List[Dict[str, Any]]:
    """실거래가 수집 작업.

    현재 월 + 직전 월의 실거래가 데이터를 수집합니다.
    """
    from app.services.real_transaction_service import collect_and_save
    from app.models.database import SessionLocal

    start_time = datetime.now()
    # 현재 월 + 직전 월 수집
    current_ymd = start_time.strftime("%Y%m")
    prev_month = start_time.month - 1
    prev_year = start_time.year if prev_month > 0 else start_time.year - 1
    prev_month = prev_month if prev_month > 0 else 12
    prev_ymd = f"{prev_year}{prev_month:02d}"

    deal_ymds = [prev_ymd, current_ymd]
    logger.info(
        "===== 실거래가 수집 시작: %s (계약월: %s) =====",
        start_time.isoformat(), ", ".join(deal_ymds),
    )

    db = SessionLocal()
    try:
        results = []
        for deal_ymd in deal_ymds:
            for region in settings.TARGET_REGIONS:
                sido = region.get("sido", "")
                sigungu = region.get("sigungu", "")
                if not sido or not sigungu:
                    continue

                try:
                    stats = await collect_and_save(db, sido, sigungu, deal_ymd)
                    results.append(stats)
                except Exception as e:
                    logger.error(
                        "실거래가 수집 실패 (%s %s %s): %s",
                        sido, sigungu, deal_ymd, str(e),
                    )

        total_saved = sum(r.get("saved", 0) for r in results)
        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info(
            "실거래가 수집 완료: %.1f초, %d개 지역, %d건 저장",
            elapsed, len(results), total_saved,
        )
        return results

    except Exception as e:
        logger.error("실거래가 수집 실패: %s", str(e), exc_info=True)
        return []
    finally:
        db.close()


def run_complex_comparison_job() -> Dict[str, Any]:
    """단지별 KB시세 vs 실거래가 비교 업데이트 작업."""
    from app.services.complex_comparison_service import update_all_comparisons
    from app.models.database import SessionLocal

    start_time = datetime.now()
    logger.info("===== 단지 비교 업데이트 시작: %s =====", start_time.isoformat())

    db = SessionLocal()
    try:
        result = update_all_comparisons(db)
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            "단지 비교 완료: %.1f초, %d건 업데이트",
            elapsed, result.get("updated", 0),
        )
        return result
    except Exception as e:
        logger.error("단지 비교 실패: %s", str(e), exc_info=True)
        return {}
    finally:
        db.close()


# ──────────────────────────────────────────
# 스케줄러 관리
# ──────────────────────────────────────────

def start_scheduler() -> AsyncIOScheduler:
    """데이터 수집 스케줄러를 시작합니다.

    등록 작업:
    - KB시세 수집: 매일 KB_PRICE_CRON_HOUR시 (기본 06:00)
    - 실거래가 수집: 매일 02:00
    - 단지 비교 업데이트: 매일 07:00 (KB시세 수집 후)
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("스케줄러가 이미 실행 중입니다")
        return _scheduler

    _scheduler = AsyncIOScheduler()

    kb_hour = settings.KB_PRICE_CRON_HOUR
    kb_minute = settings.KB_PRICE_CRON_MINUTE

    # 잡 1: KB시세 수집 (매일 1회)
    _scheduler.add_job(
        run_kb_price_job,
        trigger=CronTrigger(hour=kb_hour, minute=kb_minute),
        id="kb_price_job",
        name="KB시세 수집",
        replace_existing=True,
        max_instances=1,
    )

    # 잡 2: 실거래가 수집 (매일 새벽 2시)
    _scheduler.add_job(
        run_real_transaction_job,
        trigger=CronTrigger(hour=2, minute=0),
        id="real_transaction_job",
        name="실거래가 수집",
        replace_existing=True,
        max_instances=1,
    )

    # 잡 3: 단지 비교 업데이트 (매일 07:00, KB시세 수집 후)
    _scheduler.add_job(
        run_complex_comparison_job,
        trigger=CronTrigger(hour=7, minute=0),
        id="complex_comparison_job",
        name="단지 비교 업데이트",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info(
        "스케줄러 시작: KB시세 매일 %02d:%02d, 실거래가 매일 02:00, "
        "단지비교 매일 07:00, 대상 %d개 지역",
        kb_hour, kb_minute, len(settings.TARGET_REGIONS),
    )

    return _scheduler


def stop_scheduler():
    """스케줄러를 중지합니다."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("스케줄러 중지됨")
    _scheduler = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """현재 스케줄러 인스턴스를 반환합니다."""
    return _scheduler


async def run_once():
    """KB시세 + 실거래가 + 비교를 한 번 즉시 실행합니다 (테스트/수동용)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    await run_kb_price_job()
    await run_real_transaction_job()
    run_complex_comparison_job()


if __name__ == "__main__":
    asyncio.run(run_once())
