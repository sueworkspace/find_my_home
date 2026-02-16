"""
APScheduler 기반 크롤링 스케줄러

1시간 간격으로 네이버 부동산 매물 크롤링을 실행합니다.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.crawler.naver_crawler import NaverCrawler
from config.settings import settings

logger = logging.getLogger(__name__)

# 전역 스케줄러 인스턴스
_scheduler: Optional[AsyncIOScheduler] = None


async def run_crawl_job():
    """크롤링 작업 실행 (스케줄러에서 호출).

    settings.TARGET_REGIONS에 설정된 모든 지역을 크롤링합니다.
    """
    start_time = datetime.now()
    logger.info("===== 스케줄러 크롤링 작업 시작: %s =====", start_time.isoformat())

    crawler = NaverCrawler(target_regions=settings.TARGET_REGIONS)

    try:
        results = await crawler.crawl_all_target_regions()

        total_articles = sum(r.get("articles_saved", 0) for r in results)
        total_errors = sum(r.get("errors", 0) for r in results)
        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info(
            "===== 스케줄러 크롤링 작업 완료 =====\n"
            "  소요 시간: %.1f초\n"
            "  처리 지역: %d개\n"
            "  저장된 매물: %d개\n"
            "  에러: %d건",
            elapsed, len(results), total_articles, total_errors,
        )

        return results

    except Exception as e:
        logger.error("스케줄러 크롤링 작업 실패: %s", str(e), exc_info=True)
        raise
    finally:
        await crawler.close()


def start_scheduler() -> AsyncIOScheduler:
    """크롤링 스케줄러를 시작합니다.

    - CRAWLER_INTERVAL_MINUTES 간격으로 반복 실행 (기본 60분)
    - 애플리케이션 시작 시 호출
    - 시작 즉시 첫 실행 후, 이후 주기적 실행

    Returns:
        AsyncIOScheduler 인스턴스
    """
    global _scheduler

    if _scheduler and _scheduler.running:
        logger.warning("스케줄러가 이미 실행 중입니다")
        return _scheduler

    _scheduler = AsyncIOScheduler()

    interval_minutes = settings.CRAWLER_INTERVAL_MINUTES

    _scheduler.add_job(
        run_crawl_job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="naver_crawl_job",
        name="네이버 부동산 매물 크롤링",
        replace_existing=True,
        max_instances=1,  # 이전 작업이 끝나지 않으면 다음 실행 스킵
    )

    _scheduler.start()
    logger.info(
        "크롤링 스케줄러 시작: %d분 간격, 대상 지역 %d개",
        interval_minutes,
        len(settings.TARGET_REGIONS),
    )

    return _scheduler


def stop_scheduler():
    """크롤링 스케줄러를 중지합니다."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("크롤링 스케줄러 중지됨")
    _scheduler = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """현재 스케줄러 인스턴스를 반환합니다."""
    return _scheduler


async def run_once():
    """스케줄러 없이 크롤링을 한 번 즉시 실행합니다.

    테스트나 수동 실행 시 사용:
        python -m app.crawler.scheduler
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    results = await run_crawl_job()
    return results


if __name__ == "__main__":
    asyncio.run(run_once())
