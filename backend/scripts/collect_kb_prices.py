"""
KB시세 전체 수집 스크립트

실거래가 배치 수집 완료 후, 수집된 모든 단지에 대해 KB시세를 조회합니다.
- ApartmentComplex 테이블의 모든 단지를 지역별로 순차 처리
- 진행 상황을 파일에 저장하여 재시작 시 이어서 진행 가능
- 로그는 collect_kb_prices.log에 저장

사용법:
    python scripts/collect_kb_prices.py [--resume]
    python scripts/collect_kb_prices.py  # 처음부터
    python scripts/collect_kb_prices.py --resume  # 이어서

진행 파일: scripts/kb_progress.json
    {"completed": ["서울특별시_강남구", "서울특별시_서초구", ...]}
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (상대 임포트 대신 절대 임포트 사용)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.kb_price_service import KBPriceService
from app.crawler.real_transaction_client import SIGUNGU_CODE_MAP

# ──────────────────────────────────────────
# 로그 설정
# ──────────────────────────────────────────
LOG_FILE = project_root / "scripts" / "collect_kb_prices.log"
PROGRESS_FILE = project_root / "scripts" / "kb_progress.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def load_progress() -> set:
    """이전 진행 상황을 로드한다."""
    if not PROGRESS_FILE.exists():
        return set()
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("completed", []))
    except Exception:
        return set()


def save_progress(completed: set):
    """진행 상황을 파일에 저장한다."""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"completed": sorted(completed)}, f, ensure_ascii=False, indent=2)


async def run(resume: bool = False):
    """모든 지역의 KB시세를 순차 수집한다.

    Args:
        resume: True이면 이전 진행 상황에서 이어서 실행
    """
    # 전체 지역 목록 구성
    all_regions = []
    for sido, sigungu_map in SIGUNGU_CODE_MAP.items():
        for sigungu in sigungu_map.keys():
            all_regions.append((sido, sigungu))

    total_regions = len(all_regions)
    logger.info("KB시세 배치 수집 시작: 전체 %d개 지역", total_regions)

    # 진행 상황 로드
    completed = load_progress() if resume else set()
    if resume and completed:
        logger.info("이전 진행 이어서 수집: %d개 지역 완료됨", len(completed))

    service = KBPriceService()
    total_saved = 0
    total_matched = 0

    try:
        for idx, (sido, sigungu) in enumerate(all_regions, 1):
            region_key = f"{sido}_{sigungu}"

            # 이미 완료된 지역은 스킵
            if region_key in completed:
                logger.info("[%d/%d] 스킵 (완료): %s %s", idx, total_regions, sido, sigungu)
                continue

            logger.info(
                "[%d/%d] KB시세 수집: %s %s",
                idx, total_regions, sido, sigungu
            )

            try:
                stats = await service.update_kb_prices_for_region(sido, sigungu)
                matched = stats.get("matched_complexes", 0)
                saved = stats.get("prices_saved", 0)
                total_matched += matched
                total_saved += saved

                logger.info(
                    "[%d/%d] 완료: %s %s | 매칭=%d, 저장=%d | 누적저장=%d",
                    idx, total_regions, sido, sigungu, matched, saved, total_saved,
                )

                completed.add(region_key)
                save_progress(completed)

            except Exception as e:
                logger.error(
                    "[%d/%d] 에러: %s %s - %s",
                    idx, total_regions, sido, sigungu, str(e),
                    exc_info=True,
                )
                # 에러 발생해도 계속 진행

    finally:
        await service.close()

    logger.info(
        "===== KB시세 배치 수집 완료 =====\n"
        "  처리 지역: %d / %d\n"
        "  총 매칭 성공: %d개 단지\n"
        "  총 저장된 시세: %d개 항목",
        len(completed), total_regions, total_matched, total_saved,
    )

    # 진행 파일 정리 (완료 시)
    if len(completed) >= total_regions:
        logger.info("모든 지역 처리 완료. 진행 파일을 초기화합니다.")
        save_progress(set())


if __name__ == "__main__":
    resume = "--resume" in sys.argv
    asyncio.run(run(resume=resume))
