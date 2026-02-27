#!/usr/bin/env python3
"""
총세대수(total_units) + 좌표(lat/lng) 배치 수집 스크립트

KB `brif` API를 호출하여 매칭된 단지의 총세대수와 좌표를 DB에 저장합니다.
기존에 total_units가 NULL인 단지만 대상으로 합니다.

사용법:
    cd backend
    venv/bin/python scripts/collect_total_units.py [--concurrency 5] [--dry-run]
"""

import argparse
import asyncio
import logging
import sys
import time
from collections import defaultdict
from typing import Dict, List

sys.path.insert(0, ".")

from app.crawler.kb_price_client import KBPriceClient
from app.models.apartment import ApartmentComplex
from app.models.database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def collect_brif_for_dong(
    client: KBPriceClient,
    dong_code: str,
    complexes: List[ApartmentComplex],
    semaphore: asyncio.Semaphore,
    db,
    dry_run: bool = False,
) -> Dict[str, int]:
    """하나의 dong_code에 속한 단지들의 총세대수를 수집."""
    async with semaphore:
        stats = {"updated": 0, "failed": 0, "skipped": 0}

        # 1. KB 단지 목록 조회
        try:
            kb_list = await client.get_complex_list(dong_code)
        except Exception as e:
            logger.error("get_complex_list 실패 dong=%s: %s", dong_code, e)
            stats["failed"] = len(complexes)
            return stats

        if not kb_list:
            stats["skipped"] = len(complexes)
            return stats

        # 2. 각 단지 매칭 → brif 조회
        for cpx in complexes:
            try:
                matched = client.match_from_list(cpx.name, kb_list, dong=cpx.dong)
                if not matched:
                    stats["failed"] += 1
                    continue

                kb_id = int(matched["단지기본일련번호"])
                brif = await client.get_complex_brif(kb_id)

                if not brif:
                    stats["failed"] += 1
                    continue

                total_units = brif.get("총세대수")
                lat = brif.get("wgs84위도")
                lng = brif.get("wgs84경도")

                if dry_run:
                    logger.info(
                        "[DRY-RUN] %s: 세대수=%s, lat=%s, lng=%s",
                        cpx.name, total_units, lat, lng,
                    )
                    stats["updated"] += 1
                    continue

                changed = False
                if total_units and cpx.total_units is None:
                    cpx.total_units = int(total_units)
                    changed = True
                if lat and cpx.lat is None:
                    cpx.lat = float(lat)
                    changed = True
                if lng and cpx.lng is None:
                    cpx.lng = float(lng)
                    changed = True

                if changed:
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1

            except Exception as e:
                logger.error("brif 수집 실패 [%d] %s: %s", cpx.id, cpx.name, e)
                stats["failed"] += 1

        # 동 단위로 커밋
        if not dry_run:
            try:
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error("커밋 실패 dong=%s: %s", dong_code, e)

        return stats


async def main(concurrency: int = 5, dry_run: bool = False):
    """메인 실행 함수."""
    start = time.time()
    client = KBPriceClient()
    db = SessionLocal()

    try:
        # total_units가 NULL이고 dong_code가 있는 단지만 대상
        complexes = (
            db.query(ApartmentComplex)
            .filter(
                ApartmentComplex.dong_code.isnot(None),
                ApartmentComplex.total_units.is_(None),
            )
            .all()
        )

        if not complexes:
            logger.info("총세대수 수집 대상 없음 (모든 단지가 이미 수집됨)")
            return

        # dong_code별 그룹화
        dong_groups: Dict[str, List[ApartmentComplex]] = defaultdict(list)
        for c in complexes:
            dong_groups[c.dong_code].append(c)

        logger.info(
            "총세대수 수집 시작: %d개 단지 / %d개 동 (concurrency=%d)%s",
            len(complexes), len(dong_groups), concurrency,
            " [DRY-RUN]" if dry_run else "",
        )

        # 병렬 처리
        semaphore = asyncio.Semaphore(concurrency)
        tasks = [
            collect_brif_for_dong(client, dc, group, semaphore, db, dry_run)
            for dc, group in dong_groups.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 통계 집계
        total = {"updated": 0, "failed": 0, "skipped": 0, "errors": 0}
        for r in results:
            if isinstance(r, Exception):
                total["errors"] += 1
                logger.error("동 처리 예외: %s", r)
            elif isinstance(r, dict):
                for k in ("updated", "failed", "skipped"):
                    total[k] += r.get(k, 0)

        elapsed = time.time() - start
        logger.info(
            "===== 총세대수 수집 완료 =====\n"
            "  소요시간: %.1f초 (%.1f분)\n"
            "  수집 성공: %d개\n"
            "  매칭 실패: %d개\n"
            "  스킵(이미 있음): %d개\n"
            "  에러: %d건",
            elapsed, elapsed / 60,
            total["updated"], total["failed"],
            total["skipped"], total["errors"],
        )

    finally:
        db.close()
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="총세대수 + 좌표 배치 수집")
    parser.add_argument("--concurrency", type=int, default=5, help="동시 처리 수 (기본 5)")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 테스트만")
    args = parser.parse_args()

    asyncio.run(main(concurrency=args.concurrency, dry_run=args.dry_run))
