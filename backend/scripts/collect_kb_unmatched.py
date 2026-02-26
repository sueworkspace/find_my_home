"""
KB시세 미매칭 단지 타겟 수집 스크립트

기존에 KB시세가 없는 단지만 대상으로 수집하여 시간을 절약한다.
개선된 매칭 알고리즘(브랜드 통일, IPARK 등)으로 재매칭 시도.

실행:
    cd backend
    venv/bin/python scripts/collect_kb_unmatched.py [--concurrency N]
"""

import sys
import os
import asyncio
import argparse
import logging
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main(concurrency: int) -> None:
    from app.crawler.kb_price_client import KBPriceClient
    from app.services.kb_price_service import _upsert_kb_prices
    from app.models.database import SessionLocal
    from app.models.apartment import ApartmentComplex, KBPrice
    from sqlalchemy import func

    db = SessionLocal()
    try:
        # KB시세가 없는 단지만 조회
        matched_ids = db.query(KBPrice.complex_id).distinct().subquery()
        unmatched = (
            db.query(ApartmentComplex)
            .filter(ApartmentComplex.dong_code.isnot(None))
            .filter(~ApartmentComplex.id.in_(matched_ids))
            .all()
        )

        total = db.query(ApartmentComplex).count()
        current_kb = db.query(func.count(func.distinct(KBPrice.complex_id))).scalar()
    finally:
        db.close()

    logger.info(
        "=== KB시세 미매칭 타겟 수집 시작 ===\n"
        "  전체 단지: %d개\n"
        "  현재 KB매칭: %d개 (%.1f%%)\n"
        "  미매칭 대상: %d개\n"
        "  동시 처리: %d",
        total, current_kb, current_kb / max(total, 1) * 100,
        len(unmatched), concurrency,
    )

    if not unmatched:
        logger.info("미매칭 단지 없음 — 수집 완료")
        return

    # dong_code별로 그룹화
    dong_groups = defaultdict(list)
    for c in unmatched:
        dong_groups[c.dong_code].append(c)

    logger.info(
        "미매칭 단지: %d개 / %d개 동 그룹 (평균 %.1f개/동)",
        len(unmatched), len(dong_groups),
        len(unmatched) / max(len(dong_groups), 1),
    )

    # 병렬 수집
    client = KBPriceClient()
    semaphore = asyncio.Semaphore(concurrency)
    stats = {"matched": 0, "saved": 0, "failed": 0, "errors": 0}
    processed_dongs = 0
    total_dongs = len(dong_groups)
    start = time.time()

    async def process_dong(dong_code, complexes):
        nonlocal processed_dongs
        async with semaphore:
            local_db = SessionLocal()
            try:
                kb_list = await client.get_complex_list(dong_code)
                if not kb_list:
                    stats["failed"] += len(complexes)
                    return

                for cx in complexes:
                    try:
                        matched = client.match_from_list(
                            cx.name, kb_list, dong=cx.dong,
                        )
                        if not matched:
                            stats["failed"] += 1
                            continue

                        kb_id = int(matched["단지기본일련번호"])
                        prices = await client.get_all_prices(kb_id)

                        if prices:
                            saved = _upsert_kb_prices(local_db, cx.id, prices)
                            local_db.commit()
                            stats["matched"] += 1
                            stats["saved"] += saved
                        else:
                            stats["failed"] += 1
                    except Exception as e:
                        local_db.rollback()
                        stats["failed"] += 1
                        logger.error("단지 처리 실패 [%d] %s: %s", cx.id, cx.name, e)
            except Exception as e:
                stats["errors"] += 1
                logger.error("동 처리 실패 %s: %s", dong_code, e)
            finally:
                local_db.close()
                processed_dongs += 1
                if processed_dongs % 50 == 0:
                    elapsed = time.time() - start
                    logger.info(
                        "진행: %d/%d 동 (%.0f%%) | 매칭: %d | 실패: %d | %.1f분 경과",
                        processed_dongs, total_dongs,
                        processed_dongs / total_dongs * 100,
                        stats["matched"], stats["failed"], elapsed / 60,
                    )

    tasks = [
        process_dong(dong_code, group)
        for dong_code, group in dong_groups.items()
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    await client.close()

    elapsed = time.time() - start

    # 최종 결과 확인
    db = SessionLocal()
    try:
        final_kb = db.query(func.count(func.distinct(KBPrice.complex_id))).scalar()
    finally:
        db.close()

    new_matches = final_kb - current_kb
    logger.info(
        "=== KB시세 미매칭 타겟 수집 완료 ===\n"
        "  소요시간: %.1f분\n"
        "  신규 매칭: %d개\n"
        "  시세 저장: %d개 항목\n"
        "  매칭 실패: %d개 (KB 미등록 포함)\n"
        "  에러: %d건\n"
        "  최종 커버리지: %d/%d (%.1f%%)",
        elapsed / 60,
        new_matches,
        stats["saved"],
        stats["failed"],
        stats["errors"],
        final_kb, total, final_kb / max(total, 1) * 100,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KB시세 미매칭 타겟 수집")
    parser.add_argument(
        "--concurrency", type=int, default=5,
        help="동시 처리 동(dong) 수 (기본 5)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.concurrency))
