"""
APScheduler 기반 데이터 수집 파이프라인 스케줄러

증분 아키텍처:
  - 네이버 매물 크롤링 + 가격 비교: NAVER_CRAWL_INTERVAL_MINUTES 간격 (기본 150분)
    → 첫 실행(DB 비어있음)은 전체 크롤링, 이후 증분 크롤링
  - KB시세 수집: 매일 KB_PRICE_CRON_HOUR시 (기본 06:00)
  - 실거래가 수집: 매일 02:00
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings

logger = logging.getLogger(__name__)

# 전역 스케줄러 인스턴스
_scheduler: Optional[AsyncIOScheduler] = None


# ──────────────────────────────────────────
# 헬퍼: 첫 실행 여부 판단
# ──────────────────────────────────────────

def _is_first_run() -> bool:
    """DB에 아파트 단지 데이터가 없으면 첫 실행으로 판단."""
    from app.models.apartment import ApartmentComplex
    from app.models.database import SessionLocal

    db = SessionLocal()
    try:
        count = db.query(ApartmentComplex).count()
        return count == 0
    finally:
        db.close()


# ──────────────────────────────────────────
# 개별 작업 함수
# ──────────────────────────────────────────

async def run_naver_crawl_job() -> List[Dict[str, Any]]:
    """네이버 부동산 매물 크롤링 작업.

    첫 실행(DB 비어있음): 전체 크롤링
    이후: 증분 크롤링 (변화 감지된 단지만)
    """
    from app.crawler.naver_crawler import NaverCrawler

    first_run = _is_first_run()
    mode = "전체" if first_run else "증분"
    start_time = datetime.now()
    logger.info("===== 네이버 크롤링 시작 [%s]: %s =====", mode, start_time.isoformat())

    crawler = NaverCrawler(target_regions=settings.TARGET_REGIONS)
    try:
        if first_run:
            results = await crawler.crawl_all_target_regions()
        else:
            results = await crawler.crawl_all_target_regions_incremental()

        total_articles = sum(r.get("articles_saved", 0) for r in results)
        total_errors = sum(r.get("errors", 0) for r in results)
        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info(
            "네이버 크롤링 완료 [%s]: %.1f초, %d개 지역, %d개 매물, %d건 에러",
            mode, elapsed, len(results), total_articles, total_errors,
        )
        return results

    except Exception as e:
        logger.error("네이버 크롤링 실패 [%s]: %s", mode, str(e), exc_info=True)
        return []
    finally:
        await crawler.close()


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


def run_comparison_job() -> List[Dict[str, Any]]:
    """가격 비교 작업.

    모든 활성 매물에 대해 KB시세와 호가를 비교하고 할인율을 계산합니다.
    """
    from app.services.price_comparison_service import compare_all_listings
    from app.models.database import SessionLocal

    start_time = datetime.now()
    logger.info("===== 가격 비교 시작: %s =====", start_time.isoformat())

    db = SessionLocal()
    try:
        results = []
        for region in settings.TARGET_REGIONS:
            sido = region.get("sido", "")
            sigungu = region.get("sigungu", "")
            if sido and sigungu:
                stats = compare_all_listings(db, sido, sigungu)
                results.append({"sido": sido, "sigungu": sigungu, **stats})

        total_compared = sum(r.get("compared", 0) for r in results)
        total_bargains = sum(r.get("bargains", 0) for r in results)
        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info(
            "가격 비교 완료: %.1f초, %d건 비교, %d건 급매 발견",
            elapsed, total_compared, total_bargains,
        )
        return results

    except Exception as e:
        logger.error("가격 비교 실패: %s", str(e), exc_info=True)
        return []
    finally:
        db.close()


async def run_real_transaction_job() -> List[Dict[str, Any]]:
    """실거래가 수집 작업.

    현재 월의 실거래가 데이터를 수집합니다.
    """
    from app.services.real_transaction_service import collect_and_save
    from app.models.database import SessionLocal

    start_time = datetime.now()
    # 현재 월 기준 수집 (YYYYMM)
    deal_ymd = start_time.strftime("%Y%m")
    logger.info(
        "===== 실거래가 수집 시작: %s (계약월: %s) =====",
        start_time.isoformat(), deal_ymd,
    )

    db = SessionLocal()
    try:
        results = []
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
                    "실거래가 수집 실패 (%s %s): %s",
                    sido, sigungu, str(e),
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


# ──────────────────────────────────────────
# 파이프라인: 네이버 크롤링 → 가격 비교
# ──────────────────────────────────────────

async def run_naver_then_compare() -> Dict[str, Any]:
    """네이버 크롤링 후 가격 비교를 체인 실행.

    KB시세는 별도 스케줄(매일 1회)이므로 여기서 호출하지 않음.
    """
    pipeline_start = datetime.now()
    logger.info(
        "========== 네이버+비교 파이프라인 시작: %s ==========",
        pipeline_start.isoformat(),
    )

    # 1단계: 네이버 매물 크롤링 (자동으로 전체/증분 분기)
    naver_results = await run_naver_crawl_job()

    # 2단계: 가격 비교 (기존 KB시세 데이터 기반)
    comparison_results = run_comparison_job()

    elapsed = (datetime.now() - pipeline_start).total_seconds()
    logger.info(
        "========== 네이버+비교 파이프라인 완료: %.1f초 ==========",
        elapsed,
    )

    return {
        "naver": naver_results,
        "comparisons": comparison_results,
        "elapsed_seconds": round(elapsed, 1),
    }


# 하위호환: 기존 run_full_pipeline 유지
async def run_full_pipeline() -> Dict[str, Any]:
    """전체 데이터 수집 파이프라인을 순차적으로 실행 (하위호환용).

    1. 네이버 부동산 매물 크롤링
    2. KB시세 수집
    3. 가격 비교 (할인율 산출)
    """
    pipeline_start = datetime.now()
    logger.info(
        "========== 전체 파이프라인 시작: %s ==========",
        pipeline_start.isoformat(),
    )

    naver_results = await run_naver_crawl_job()
    kb_results = await run_kb_price_job()
    comparison_results = run_comparison_job()

    elapsed = (datetime.now() - pipeline_start).total_seconds()
    logger.info(
        "========== 전체 파이프라인 완료: %.1f초 ==========",
        elapsed,
    )

    return {
        "naver": naver_results,
        "kb_prices": kb_results,
        "comparisons": comparison_results,
        "elapsed_seconds": round(elapsed, 1),
    }


# ──────────────────────────────────────────
# 스케줄러 관리
# ──────────────────────────────────────────

def start_scheduler() -> AsyncIOScheduler:
    """데이터 수집 스케줄러를 시작합니다.

    등록 작업 (3분할):
    - 네이버 크롤링 + 가격 비교: NAVER_CRAWL_INTERVAL_MINUTES 간격 (기본 150분)
    - KB시세 수집: 매일 KB_PRICE_CRON_HOUR시 (기본 06:00)
    - 실거래가 수집: 매일 02:00

    Returns:
        AsyncIOScheduler 인스턴스
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("스케줄러가 이미 실행 중입니다")
        return _scheduler

    _scheduler = AsyncIOScheduler()

    naver_interval = settings.NAVER_CRAWL_INTERVAL_MINUTES
    kb_hour = settings.KB_PRICE_CRON_HOUR
    kb_minute = settings.KB_PRICE_CRON_MINUTE

    # 잡 1: 네이버 크롤링(전체/증분 자동 분기) + 가격 비교
    _scheduler.add_job(
        run_naver_then_compare,
        trigger=IntervalTrigger(minutes=naver_interval),
        id="naver_compare_job",
        name="네이버 크롤링 + 가격 비교",
        replace_existing=True,
        max_instances=1,
    )

    # 잡 2: KB시세 수집 (매일 1회)
    _scheduler.add_job(
        run_kb_price_job,
        trigger=CronTrigger(hour=kb_hour, minute=kb_minute),
        id="kb_price_job",
        name="KB시세 수집",
        replace_existing=True,
        max_instances=1,
    )

    # 잡 3: 실거래가 수집 (매일 새벽 2시)
    _scheduler.add_job(
        run_real_transaction_job,
        trigger=CronTrigger(hour=2, minute=0),
        id="real_transaction_job",
        name="실거래가 수집",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info(
        "스케줄러 시작: 네이버+비교 %d분 간격, KB시세 매일 %02d:%02d, "
        "실거래가 매일 02:00, 대상 %d개 지역",
        naver_interval, kb_hour, kb_minute,
        len(settings.TARGET_REGIONS),
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


# ──────────────────────────────────────────
# 수동 실행 지원
# ──────────────────────────────────────────

async def run_once():
    """스케줄러 없이 네이버+비교 파이프라인을 한 번 즉시 실행합니다.

    테스트나 수동 실행 시 사용:
        python -m app.crawler.scheduler
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    results = await run_naver_then_compare()
    return results


if __name__ == "__main__":
    asyncio.run(run_once())
