"""
실거래가 과거 데이터 배치 수집 스크립트

110개 지역 × 지정 기간의 실거래가를 순차 수집합니다.
진행 상황을 JSON 파일에 저장하여 중단 후 재시작이 가능합니다.

사용법:
    python scripts/collect_historical.py                  # 2024-01 ~ 현재까지
    python scripts/collect_historical.py 202401 202501    # 기간 직접 지정

환경:
    - backend/ 디렉토리에서 실행 (venv 활성화 후)
    - .env에 DATA_GO_KR_API_KEY 설정 필요
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# backend 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.database import SessionLocal
from app.services.real_transaction_service import collect_and_save
from config.settings import settings

# ── 로깅 설정 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("collect_historical.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── 진행 상황 저장 파일 ──
PROGRESS_FILE = Path(__file__).parent / "collect_progress.json"

# ── API 요청 간격 (초): data.go.kr 호출 사이 딜레이 ──
CALL_DELAY_SECONDS = 2.0


def _get_months(start_ymd: str, end_ymd: str) -> list[str]:
    """start_ymd ~ end_ymd 사이의 모든 YYYYMM 문자열 리스트 반환."""
    months = []
    y, m = int(start_ymd[:4]), int(start_ymd[4:6])
    ey, em = int(end_ymd[:4]), int(end_ymd[4:6])
    while (y, m) <= (ey, em):
        months.append(f"{y}{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def _load_progress() -> set:
    """완료된 (sido, sigungu, yyyymm) 조합을 set으로 반환."""
    if not PROGRESS_FILE.exists():
        return set()
    with open(PROGRESS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return set(tuple(item) for item in data.get("done", []))


def _save_progress(done: set) -> None:
    """완료된 조합을 JSON 파일에 저장."""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"done": [list(item) for item in done]}, f, ensure_ascii=False, indent=2)


async def run(start_ymd: str, end_ymd: str) -> None:
    """지정 기간의 실거래가를 모든 TARGET_REGIONS에 대해 수집한다."""

    regions = settings.TARGET_REGIONS
    months = _get_months(start_ymd, end_ymd)
    done = _load_progress()

    total = len(regions) * len(months)
    completed = sum(
        1 for r in regions for m in months
        if (r["sido"], r["sigungu"], m) in done
    )

    logger.info("=" * 60)
    logger.info("실거래가 배치 수집 시작")
    logger.info("기간: %s ~ %s (%d개월)", start_ymd, end_ymd, len(months))
    logger.info("지역: %d개", len(regions))
    logger.info("총 작업: %d건 (완료: %d, 남은: %d)", total, completed, total - completed)
    logger.info("=" * 60)

    total_saved = 0
    total_created = 0
    errors = 0

    for month_idx, deal_ymd in enumerate(months, 1):
        for reg_idx, region in enumerate(regions, 1):
            sido = region["sido"]
            sigungu = region["sigungu"]
            key = (sido, sigungu, deal_ymd)

            if key in done:
                continue  # 이미 수집된 조합 건너뜀

            label = f"[{deal_ymd}] {sido} {sigungu}"
            db = SessionLocal()
            try:
                result = await collect_and_save(db, sido, sigungu, deal_ymd)
                saved = result.get("saved", 0)
                created = result.get("created", 0)
                total_saved += saved
                total_created += created

                done.add(key)
                _save_progress(done)

                logger.info(
                    "%-30s | 수집=%d, 저장=%d, 신규단지=%d | 누적저장=%d",
                    label, result.get("fetched", 0), saved, created, total_saved,
                )

            except Exception as e:
                errors += 1
                logger.error("수집 실패: %s → %s", label, e)

            finally:
                db.close()

            # API 호출 간 딜레이
            await asyncio.sleep(CALL_DELAY_SECONDS)

        # 월 단위 중간 보고
        logger.info(
            "── %s 완료 (%d/%d월) | 누적 저장=%d, 신규단지=%d, 에러=%d",
            deal_ymd, month_idx, len(months), total_saved, total_created, errors,
        )

    logger.info("=" * 60)
    logger.info("배치 수집 완료")
    logger.info("총 저장: %d건 | 신규 단지: %d개 | 에러: %d건", total_saved, total_created, errors)
    logger.info("=" * 60)


if __name__ == "__main__":
    # 기본: 2024-01 ~ 현재 월
    now = datetime.now()
    default_start = "202401"
    default_end = f"{now.year}{now.month:02d}"

    start = sys.argv[1] if len(sys.argv) > 1 else default_start
    end   = sys.argv[2] if len(sys.argv) > 2 else default_end

    asyncio.run(run(start, end))
