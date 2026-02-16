"""
실거래가 데이터 저장 및 조회 서비스

국토교통부 API에서 수집한 실거래가 데이터를 DB에 저장하고,
네이버 부동산 단지와 매칭하여 조회하는 비즈니스 로직을 담당합니다.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.models.apartment import ApartmentComplex, RealTransaction
from app.crawler.real_transaction_client import RealTransactionClient, get_lawd_cd

logger = logging.getLogger(__name__)


def _match_complex(
    db: Session,
    apt_name: str,
    sido: str,
    sigungu: str,
) -> Optional[int]:
    """아파트명과 지역 정보로 DB의 ApartmentComplex를 매칭한다.

    매칭 전략:
      1. 정확히 일치하는 이름 검색 (시/도 + 시/군/구 + 아파트명)
      2. 아파트명이 포함된 단지 검색 (LIKE 검색)

    Args:
        db: SQLAlchemy 세션
        apt_name: 실거래가 API에서 받은 아파트명
        sido: 시/도 이름
        sigungu: 시/군/구 이름

    Returns:
        매칭된 ApartmentComplex의 id, 실패 시 None
    """
    # 전략 1: 정확히 일치
    complex_row = (
        db.query(ApartmentComplex)
        .filter(
            ApartmentComplex.sido == sido,
            ApartmentComplex.sigungu == sigungu,
            ApartmentComplex.name == apt_name,
        )
        .first()
    )
    if complex_row is not None:
        return complex_row.id

    # 전략 2: LIKE 검색 - 아파트명이 포함된 단지
    # 예: API "래미안대치팰리스" vs DB "래미안 대치팰리스" (공백 차이)
    complex_row = (
        db.query(ApartmentComplex)
        .filter(
            ApartmentComplex.sido == sido,
            ApartmentComplex.sigungu == sigungu,
            ApartmentComplex.name.ilike(f"%{apt_name}%"),
        )
        .first()
    )
    if complex_row is not None:
        return complex_row.id

    # 전략 3: 아파트명에서 공백 제거 후 비교
    apt_name_no_space = apt_name.replace(" ", "")
    all_complexes = (
        db.query(ApartmentComplex)
        .filter(
            ApartmentComplex.sido == sido,
            ApartmentComplex.sigungu == sigungu,
        )
        .all()
    )
    for cpx in all_complexes:
        if cpx.name.replace(" ", "") == apt_name_no_space:
            return cpx.id

    return None


def _is_duplicate(
    db: Session,
    complex_id: int,
    area_sqm: float,
    floor: Optional[int],
    deal_date: datetime,
    deal_price: int,
) -> bool:
    """동일한 실거래가 데이터가 이미 DB에 존재하는지 확인한다.

    단지 + 전용면적 + 층 + 거래일 + 거래금액이 모두 일치하면 중복으로 판단한다.

    Args:
        db: SQLAlchemy 세션
        complex_id: 아파트 단지 ID
        area_sqm: 전용면적 (m2)
        floor: 층
        deal_date: 거래일자
        deal_price: 거래금액 (만원)

    Returns:
        중복이면 True
    """
    filters = [
        RealTransaction.complex_id == complex_id,
        RealTransaction.area_sqm == area_sqm,
        RealTransaction.deal_date == deal_date,
        RealTransaction.deal_price == deal_price,
    ]
    # 층 정보가 있으면 조건에 추가, 없으면 NULL 체크
    if floor is not None:
        filters.append(RealTransaction.floor == floor)
    else:
        filters.append(RealTransaction.floor.is_(None))

    exists = db.query(RealTransaction).filter(and_(*filters)).first()
    return exists is not None


def save_transactions(
    db: Session,
    transactions: List[Dict[str, Any]],
    sido: str,
    sigungu: str,
) -> Tuple[int, int, int]:
    """실거래가 데이터를 DB에 저장한다.

    - 네이버 부동산 단지와 이름 기반으로 매칭
    - 중복 데이터는 건너뜀
    - 매칭 실패한 건은 로그만 남기고 건너뜀

    Args:
        db: SQLAlchemy 세션
        transactions: 정규화된 거래 데이터 리스트
        sido: 시/도 이름 (단지 매칭에 사용)
        sigungu: 시/군/구 이름 (단지 매칭에 사용)

    Returns:
        (저장 성공 건수, 중복 건수, 매칭 실패 건수) 튜플
    """
    saved_count = 0
    duplicate_count = 0
    unmatched_count = 0

    # 매칭 캐시: {아파트명 -> complex_id 또는 None}
    match_cache: Dict[str, Optional[int]] = {}

    for tx in transactions:
        apt_name = tx["apt_name"]

        # 캐시에서 매칭 결과 조회
        if apt_name not in match_cache:
            match_cache[apt_name] = _match_complex(db, apt_name, sido, sigungu)

        complex_id = match_cache[apt_name]
        if complex_id is None:
            unmatched_count += 1
            continue

        # 중복 확인
        if _is_duplicate(
            db,
            complex_id=complex_id,
            area_sqm=tx["area_sqm"],
            floor=tx["floor"],
            deal_date=tx["deal_date"],
            deal_price=tx["deal_price"],
        ):
            duplicate_count += 1
            continue

        # DB에 저장
        record = RealTransaction(
            complex_id=complex_id,
            area_sqm=tx["area_sqm"],
            floor=tx["floor"],
            deal_price=tx["deal_price"],
            deal_date=tx["deal_date"],
        )
        db.add(record)
        saved_count += 1

    # 일괄 커밋
    if saved_count > 0:
        db.commit()

    logger.info(
        "실거래가 저장 완료: %s %s - 저장=%d, 중복=%d, 매칭실패=%d",
        sido, sigungu, saved_count, duplicate_count, unmatched_count,
    )

    # 매칭 실패한 아파트명 목록 로깅 (디버깅용)
    unmatched_names = [
        name for name, cid in match_cache.items() if cid is None
    ]
    if unmatched_names:
        logger.debug(
            "매칭 실패 아파트명: %s", ", ".join(unmatched_names[:20]),
        )

    return saved_count, duplicate_count, unmatched_count


async def collect_and_save(
    db: Session,
    sido: str,
    sigungu: str,
    deal_ymd: str,
) -> Dict[str, Any]:
    """실거래가 데이터를 수집하고 DB에 저장하는 통합 함수.

    1. 국토교통부 API 호출 (수집)
    2. 네이버 단지와 매칭
    3. DB 저장

    Args:
        db: SQLAlchemy 세션
        sido: 시/도 이름
        sigungu: 시/군/구 이름
        deal_ymd: 계약년월 6자리 (예: "202401")

    Returns:
        수집/저장 결과 요약 딕셔너리
    """
    client = RealTransactionClient()
    try:
        # API에서 데이터 수집
        transactions = await client.fetch_by_region(sido, sigungu, deal_ymd)

        if not transactions:
            return {
                "sido": sido,
                "sigungu": sigungu,
                "deal_ymd": deal_ymd,
                "fetched": 0,
                "saved": 0,
                "duplicates": 0,
                "unmatched": 0,
            }

        # DB에 저장
        saved, duplicates, unmatched = save_transactions(
            db, transactions, sido, sigungu,
        )

        return {
            "sido": sido,
            "sigungu": sigungu,
            "deal_ymd": deal_ymd,
            "fetched": len(transactions),
            "saved": saved,
            "duplicates": duplicates,
            "unmatched": unmatched,
        }

    finally:
        await client.close()


def get_transactions_by_complex(
    db: Session,
    complex_id: int,
    limit: int = 20,
    area_sqm: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """특정 단지의 최근 실거래가를 조회한다.

    Args:
        db: SQLAlchemy 세션
        complex_id: 아파트 단지 ID (apartment_complex.id)
        limit: 최대 조회 건수 (기본 20)
        area_sqm: 전용면적 필터 (m2, 선택)

    Returns:
        실거래가 딕셔너리 리스트 (최근 거래일 순)
    """
    query = (
        db.query(
            RealTransaction.id,
            RealTransaction.area_sqm,
            RealTransaction.floor,
            RealTransaction.deal_price,
            RealTransaction.deal_date,
            ApartmentComplex.name.label("apartment_name"),
        )
        .join(
            ApartmentComplex,
            RealTransaction.complex_id == ApartmentComplex.id,
        )
        .filter(RealTransaction.complex_id == complex_id)
    )

    # 전용면적 필터 (선택)
    if area_sqm is not None:
        query = query.filter(RealTransaction.area_sqm == area_sqm)

    # 최근 거래일 순 정렬
    rows = (
        query
        .order_by(desc(RealTransaction.deal_date))
        .limit(limit)
        .all()
    )

    results: List[Dict[str, Any]] = []
    for row in rows:
        results.append({
            "id": row.id,
            "apartment_name": row.apartment_name,
            "area_sqm": round(row.area_sqm, 2),
            "floor": row.floor,
            "deal_price": row.deal_price,
            "deal_date": row.deal_date.isoformat() if row.deal_date else None,
        })

    return results


def get_transaction_summary(
    db: Session,
    complex_id: int,
    area_sqm: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """특정 단지의 실거래가 요약 통계를 반환한다.

    Args:
        db: SQLAlchemy 세션
        complex_id: 아파트 단지 ID
        area_sqm: 전용면적 필터 (m2, 선택)

    Returns:
        요약 딕셔너리 (총 건수, 최근거래가, 최고가, 최저가, 평균가),
        데이터 없으면 None
    """
    query = (
        db.query(
            func.count(RealTransaction.id).label("total_count"),
            func.max(RealTransaction.deal_price).label("max_price"),
            func.min(RealTransaction.deal_price).label("min_price"),
            func.avg(RealTransaction.deal_price).label("avg_price"),
        )
        .filter(RealTransaction.complex_id == complex_id)
    )

    if area_sqm is not None:
        query = query.filter(RealTransaction.area_sqm == area_sqm)

    result = query.first()

    if result is None or result.total_count == 0:
        return None

    # 가장 최근 거래 조회
    latest_query = (
        db.query(RealTransaction)
        .filter(RealTransaction.complex_id == complex_id)
    )
    if area_sqm is not None:
        latest_query = latest_query.filter(
            RealTransaction.area_sqm == area_sqm,
        )
    latest = latest_query.order_by(
        desc(RealTransaction.deal_date),
    ).first()

    return {
        "total_count": result.total_count,
        "max_price": result.max_price,
        "min_price": result.min_price,
        "avg_price": int(result.avg_price) if result.avg_price else None,
        "latest_price": latest.deal_price if latest else None,
        "latest_date": (
            latest.deal_date.isoformat() if latest and latest.deal_date else None
        ),
    }
