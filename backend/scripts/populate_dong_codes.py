"""
ApartmentComplex 테이블의 dong_code 컬럼을 DONG_LAWDCD_MAP으로 일괄 채우기.

KB시세 고속 수집(collect_kb_fast.py)의 전처리 단계.
dong_code가 채워진 단지만 동 단위 배치 수집 대상이 된다.

실행 방법:
    cd backend
    venv/bin/python scripts/populate_dong_codes.py

결과:
    - ApartmentComplex.dong_code 컬럼을 DONG_LAWDCD_MAP 기반으로 업데이트
    - 이미 dong_code가 있는 단지는 건너뜀
    - dong-level 코드(마지막 6자리 != '000000')만 저장
"""

import sys
import os

# backend 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from app.models.database import SessionLocal
from app.models.apartment import ApartmentComplex
from app.crawler.kb_price_client import get_lawdcd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def is_dong_level_code(code: str) -> bool:
    """동-level 법정동코드 여부 확인 (gu-level은 마지막 6자리가 000000)."""
    if not code or len(code) != 10:
        return False
    # gu-level: 예) "1168000000" → 마지막 6자리 000000
    # dong-level: 예) "1168010600" → 마지막 6자리 010600
    return code[-6:] != "000000"


def populate_dong_codes() -> None:
    """DONG_LAWDCD_MAP을 이용해 dong_code가 없는 단지에 동-level 코드를 채운다."""
    db = SessionLocal()
    try:
        # dong_code가 없는 단지 전체 조회
        complexes = (
            db.query(ApartmentComplex)
            .filter(ApartmentComplex.dong_code.is_(None))
            .all()
        )

        total = len(complexes)
        logger.info("dong_code 없는 단지 수: %d개", total)

        updated = 0
        skipped_no_code = 0
        skipped_gu_level = 0

        for i, c in enumerate(complexes, 1):
            if i % 500 == 0:
                logger.info("진행: %d/%d (업데이트: %d)", i, total, updated)

            # DONG_LAWDCD_MAP에서 동-level 코드 조회
            code = get_lawdcd(c.sido, c.sigungu, c.dong)

            if not code:
                skipped_no_code += 1
                continue

            if not is_dong_level_code(code):
                # gu-level fallback 코드는 저장하지 않음 (KB API에서 빈 결과)
                skipped_gu_level += 1
                continue

            c.dong_code = code
            updated += 1

        db.commit()

        logger.info(
            "=== 완료 ===\n"
            "  대상: %d개\n"
            "  dong_code 채움: %d개\n"
            "  코드 없음(DONG_LAWDCD_MAP 미등록): %d개\n"
            "  gu-level 스킵: %d개",
            total, updated, skipped_no_code, skipped_gu_level,
        )

    except Exception as e:
        db.rollback()
        logger.error("실패: %s", e, exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    populate_dong_codes()
