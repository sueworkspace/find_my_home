"""배치 크롤러 — 전체 지역 순차 크롤링 + 쿨다운 + EC2 동기화.

매일 1회 실행하여 서울/경기/인천 전체 지역 데이터를 수집합니다.
API 호출 한도(180건)에 도달하면 10분 쿨다운 후 재개합니다.

사용법:
    python scripts/batch_crawl.py                    # 전체 지역 크롤링
    python scripts/batch_crawl.py --regions 강남구 서초구  # 특정 지역만
    python scripts/batch_crawl.py --sync-only        # DB 동기화만 (크롤링 X)
"""

import argparse
import asyncio
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from app.crawler.naver_crawler import NaverCrawler
from app.services.price_comparison_service import compare_all_listings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/batch_crawl.log"),
    ],
)
logger = logging.getLogger("batch_crawl")

# EC2 동기화 설정
EC2_HOST = "ubuntu@54.180.152.129"
EC2_KEY = str(Path.home() / "Downloads" / "find-my-home-key.pem")
DUMP_PATH = "/tmp/find_my_home_dump.sql"


async def crawl_region_with_cooldown(
    crawler: NaverCrawler,
    sido: str,
    sigungu: str,
    region_index: int,
    total_regions: int,
) -> Dict:
    """단일 지역 크롤링 + API 호출 한도 시 쿨다운."""
    logger.info(
        "━━━ [%d/%d] %s %s 크롤링 시작 ━━━",
        region_index, total_regions, sido, sigungu,
    )
    start = time.time()

    # 크롤링 전 API 호출 수 확인 → 한도 도달 시 쿨다운
    call_count = crawler.client.api_call_count
    limit = settings.BATCH_API_CALL_LIMIT
    if call_count >= limit:
        cooldown = settings.BATCH_COOLDOWN_SECONDS
        logger.info(
            "API 호출 %d건 도달 (한도 %d). %d초 쿨다운 시작...",
            call_count, limit, cooldown,
        )
        await asyncio.sleep(cooldown)
        crawler.client.api_call_count = 0  # 카운터 리셋
        logger.info("쿨다운 완료. 크롤링 재개")
    elif region_index > 1:
        # 첫 지역이 아니면 지역 간 30초 쿨다운 (차단 예방)
        logger.info("지역 간 30초 대기...")
        await asyncio.sleep(30)

    # 단일 지역 크롤링
    try:
        result = await crawler.crawl_region(sido, sigungu)
        elapsed = time.time() - start
        saved = result.get("articles_saved", 0)
        complexes = result.get("complexes_found", 0)
        logger.info(
            "✓ [%d/%d] %s %s 완료: %d개 단지, %d개 매물 (%.0f초)",
            region_index, total_regions, sido, sigungu,
            complexes, saved, elapsed,
        )
        return result
    except Exception as e:
        logger.error(
            "✗ [%d/%d] %s %s 실패: %s",
            region_index, total_regions, sido, sigungu, str(e),
        )
        return {"sido": sido, "sigungu": sigungu, "error": str(e)}


async def run_batch(regions: Optional[List[Dict[str, str]]] = None):
    """전체 지역 순차 크롤링."""
    target = regions or settings.TARGET_REGIONS
    total = len(target)

    logger.info("=" * 60)
    logger.info("배치 크롤링 시작: %d개 지역, %s", total, datetime.now().isoformat())
    logger.info("=" * 60)

    batch_start = time.time()
    results = []

    crawler = NaverCrawler(target_regions=target)
    try:
        for i, region in enumerate(target, 1):
            result = await crawl_region_with_cooldown(
                crawler,
                region["sido"],
                region["sigungu"],
                i,
                total,
            )
            results.append(result)
    finally:
        await crawler.close()

    # 크롤링 후 가격비교 실행
    logger.info("━━━ 가격비교 엔진 실행 ━━━")
    try:
        from app.models.database import SessionLocal
        db = SessionLocal()
        try:
            for region in target:
                compare_all_listings(db, region["sido"], region["sigungu"])
        finally:
            db.close()
    except Exception as e:
        logger.error("가격비교 실패: %s", str(e))

    # 결과 요약
    total_saved = sum(r.get("articles_saved", 0) for r in results)
    total_complexes = sum(r.get("complexes_found", 0) for r in results)
    total_errors = sum(1 for r in results if "error" in r)
    elapsed = time.time() - batch_start

    logger.info("=" * 60)
    logger.info("배치 크롤링 완료: %.0f초 (%.1f분)", elapsed, elapsed / 60)
    logger.info("  지역: %d개 성공, %d개 실패", total - total_errors, total_errors)
    logger.info("  단지: %d개, 매물: %d개", total_complexes, total_saved)
    logger.info("=" * 60)

    return results


def sync_to_ec2():
    """로컬 DB → EC2 동기화 (pg_dump → scp → pg_restore)."""
    logger.info("━━━ EC2 DB 동기화 시작 ━━━")

    # 1. pg_dump
    logger.info("pg_dump 실행 중...")
    dump_cmd = [
        "pg_dump", "-U", "suelee", "-d", "find_my_home",
        "--clean", "--if-exists", "-f", DUMP_PATH,
    ]
    result = subprocess.run(dump_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("pg_dump 실패: %s", result.stderr)
        return False

    logger.info("pg_dump 완료: %s", DUMP_PATH)

    # 2. scp로 EC2에 전송
    logger.info("EC2로 전송 중...")
    scp_cmd = [
        "scp", "-i", EC2_KEY, "-o", "StrictHostKeyChecking=no",
        DUMP_PATH, f"{EC2_HOST}:/tmp/find_my_home_dump.sql",
    ]
    result = subprocess.run(scp_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("scp 실패: %s", result.stderr)
        return False

    # 3. EC2에서 pg_restore
    logger.info("EC2에서 DB 복원 중...")
    restore_cmd = [
        "ssh", "-i", EC2_KEY, "-o", "StrictHostKeyChecking=no", EC2_HOST,
        "sudo docker exec -i find_my_home-db-1 "
        "psql -U suelee -d find_my_home < /tmp/find_my_home_dump.sql",
    ]
    result = subprocess.run(restore_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("pg_restore 실패: %s", result.stderr)
        return False

    logger.info("━━━ EC2 DB 동기화 완료 ━━━")
    return True


def main():
    parser = argparse.ArgumentParser(description="배치 크롤러")
    parser.add_argument(
        "--regions", nargs="+",
        help="특정 지역만 크롤링 (예: 강남구 서초구)",
    )
    parser.add_argument(
        "--sync-only", action="store_true",
        help="크롤링 없이 EC2 동기화만 실행",
    )
    parser.add_argument(
        "--no-sync", action="store_true",
        help="크롤링만 실행, EC2 동기화 하지 않음",
    )
    args = parser.parse_args()

    if args.sync_only:
        sync_to_ec2()
        return

    # 지역 필터링
    regions = None
    if args.regions:
        regions = [
            r for r in settings.TARGET_REGIONS
            if r["sigungu"] in args.regions
        ]
        if not regions:
            logger.error("일치하는 지역 없음: %s", args.regions)
            return

    # 크롤링 실행
    asyncio.run(run_batch(regions))

    # EC2 동기화
    if not args.no_sync:
        sync_to_ec2()


if __name__ == "__main__":
    main()
