"""
KB시세 고속 수집 스크립트 — 동 단위 배치 + 병렬 처리

기존 순차 수집(24시간) 대비 10~25배 빠른 수집 방법.

전제조건:
    1. ApartmentComplex.dong_code가 채워져 있어야 함
       (없으면 먼저 실행: venv/bin/python scripts/populate_dong_codes.py)

실행 방법:
    cd backend
    venv/bin/python scripts/collect_kb_fast.py [--concurrency N]

옵션:
    --concurrency N : 동시 처리 동(dong) 수 (기본 5, 최대 10 권장)

예시:
    venv/bin/python scripts/collect_kb_fast.py
    venv/bin/python scripts/collect_kb_fast.py --concurrency 8
"""

import sys
import os
import asyncio
import argparse
import logging

# backend 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main(concurrency: int) -> None:
    from app.services.kb_price_service import KBPriceService
    from app.models.database import SessionLocal
    from app.models.apartment import ApartmentComplex
    from sqlalchemy import func

    # 사전 확인: dong_code 현황
    db = SessionLocal()
    try:
        total = db.query(ApartmentComplex).count()
        with_code = db.query(ApartmentComplex).filter(
            ApartmentComplex.dong_code.isnot(None)
        ).count()
        unique_dongs = db.query(
            func.count(func.distinct(ApartmentComplex.dong_code))
        ).scalar()
    finally:
        db.close()

    logger.info(
        "=== KB시세 고속 수집 시작 ===\n"
        "  전체 단지: %d개\n"
        "  dong_code 있음: %d개 (%.1f%%)\n"
        "  고유 동 수: %d개\n"
        "  동시 처리 동 수: %d",
        total, with_code, with_code / max(total, 1) * 100,
        unique_dongs, concurrency,
    )

    if with_code == 0:
        logger.error(
            "dong_code가 없습니다! 먼저 populate_dong_codes.py를 실행하세요:\n"
            "  venv/bin/python scripts/populate_dong_codes.py"
        )
        return

    service = KBPriceService()
    try:
        stats = await service.update_kb_prices_parallel(concurrency=concurrency)
        logger.info("수집 완료: %s", stats)
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KB시세 고속 수집 (동 단위 병렬)")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="동시 처리할 동(dong) 수 (기본 5)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.concurrency))
