"""
실거래가 데이터 저장 및 조회 서비스

국토교통부 API에서 수집한 실거래가 데이터를 DB에 저장합니다.
- 기존 단지와 이름 기반 매칭
- 매칭 실패 시 실거래가 정보를 바탕으로 신규 단지 자동 생성
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.models.apartment import ApartmentComplex, RealTransaction
from app.crawler.real_transaction_client import RealTransactionClient, get_lawd_cd

logger = logging.getLogger(__name__)

# 면적 매칭 허용 오차 (m²) — 실거래가 84.97 vs 네이버 85.0 같은 차이 허용
AREA_TOLERANCE = 1.0


def _normalize_name(name: str) -> str:
    """아파트명을 정규화하여 매칭률을 높인다.

    정규화 규칙:
      1. 괄호와 그 안의 내용 제거: "개포현대(200동)" → "개포현대"
      2. 동/호 번호 제거: "현대1차101동~106동" → "현대1차"
      3. 공백, 특수문자 제거
      4. 숫자 뒤의 "차" 유지: "현대2차" → "현대2차"
    """
    # 괄호 내용 제거
    name = re.sub(r'\([^)]*\)', '', name)
    # 쉼표 이후 동 정보 제거: "1동,2동,3동" 패턴
    name = re.sub(r'[\d,]+동.*$', '', name)
    # "101동~106동", "101동~111동" 패턴 제거
    name = re.sub(r'\d+동[~\-]\d+동', '', name)
    # 끝에 붙은 동/호 번호 제거: "103동" 패턴
    name = re.sub(r'\d+동$', '', name)
    # 공백, 특수문자 제거
    name = re.sub(r'[\s\-·・]', '', name)
    return name.strip()


def _match_complex(
    db: Session,
    apt_name: str,
    sido: str,
    sigungu: str,
) -> Optional[int]:
    """아파트명과 지역 정보로 DB의 ApartmentComplex를 매칭한다.

    매칭 전략 (순서대로 시도):
      1. 정확히 일치
      2. LIKE 검색 (API명이 DB명에 포함)
      3. 공백 제거 후 비교
      4. 정규화 후 비교 (괄호/동번호 제거)
      5. 정규화명 상호 포함 (substring 양방향)

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

    # 전략 2: LIKE 검색 - API명이 DB명에 포함
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

    # 이하 전략은 전체 단지를 한 번만 조회하여 재사용
    all_complexes = (
        db.query(ApartmentComplex)
        .filter(
            ApartmentComplex.sido == sido,
            ApartmentComplex.sigungu == sigungu,
        )
        .all()
    )

    # 전략 3: 공백 제거 후 정확히 비교
    api_no_space = apt_name.replace(" ", "")
    for cpx in all_complexes:
        if cpx.name.replace(" ", "") == api_no_space:
            return cpx.id

    # 전략 4: 정규화 후 정확히 비교
    api_norm = _normalize_name(apt_name)
    if len(api_norm) >= 2:  # 너무 짧은 이름은 오매칭 방지
        for cpx in all_complexes:
            db_norm = _normalize_name(cpx.name)
            if api_norm == db_norm:
                return cpx.id

    # 전략 5: 정규화명 상호 포함 (긴 쪽이 짧은 쪽을 포함)
    if len(api_norm) >= 3:  # 최소 3글자 이상
        best_match = None
        best_len = 0
        for cpx in all_complexes:
            db_norm = _normalize_name(cpx.name)
            if len(db_norm) < 3:
                continue
            # 양방향 substring 매칭
            if api_norm in db_norm or db_norm in api_norm:
                # 더 긴 매칭을 우선 (정확도 높음)
                match_len = min(len(api_norm), len(db_norm))
                if match_len > best_len:
                    best_match = cpx.id
                    best_len = match_len
        if best_match is not None:
            return best_match

    return None


def _create_complex(
    db: Session,
    apt_name: str,
    sido: str,
    sigungu: str,
    dong: str,
    build_year: Optional[int],
) -> int:
    """실거래가 데이터를 바탕으로 신규 ApartmentComplex를 생성한다.

    네이버 데이터 없이 실거래가 API만으로 단지를 등록할 때 사용.

    Args:
        db: SQLAlchemy 세션
        apt_name: 아파트명
        sido: 시/도
        sigungu: 시/군/구
        dong: 법정동 (umd_name)
        build_year: 건축년도

    Returns:
        생성된 ApartmentComplex의 id
    """
    new_complex = ApartmentComplex(
        name=apt_name,
        sido=sido,
        sigungu=sigungu,
        dong=dong or None,
        built_year=build_year or None,
    )
    db.add(new_complex)
    db.flush()  # id 확정 (commit 전)
    logger.info("신규 단지 생성: %s %s %s (id=%d)", sido, sigungu, apt_name, new_complex.id)
    return new_complex.id


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

    - 이름 기반으로 기존 단지와 매칭
    - 매칭 실패 시 실거래가 정보로 신규 단지 자동 생성
    - 중복 데이터는 건너뜀

    Args:
        db: SQLAlchemy 세션
        transactions: 정규화된 거래 데이터 리스트
        sido: 시/도 이름 (단지 매칭에 사용)
        sigungu: 시/군/구 이름 (단지 매칭에 사용)

    Returns:
        (저장 성공 건수, 중복 건수, 신규 단지 생성 건수) 튜플
    """
    saved_count = 0
    duplicate_count = 0
    created_count = 0

    # 매칭 캐시: {아파트명 -> complex_id}
    match_cache: Dict[str, int] = {}

    for tx in transactions:
        apt_name = tx["apt_name"]

        # 캐시에서 매칭 결과 조회
        if apt_name not in match_cache:
            existing_id = _match_complex(db, apt_name, sido, sigungu)
            if existing_id is not None:
                match_cache[apt_name] = existing_id
            else:
                # 매칭 실패 → 신규 단지 자동 생성
                new_id = _create_complex(
                    db,
                    apt_name=apt_name,
                    sido=sido,
                    sigungu=sigungu,
                    dong=tx.get("umd_name", ""),
                    build_year=tx.get("build_year"),
                )
                match_cache[apt_name] = new_id
                created_count += 1

        complex_id = match_cache[apt_name]

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

    # 일괄 커밋 (신규 단지 + 실거래가)
    if saved_count > 0 or created_count > 0:
        db.commit()

    logger.info(
        "실거래가 저장 완료: %s %s - 저장=%d, 중복=%d, 신규단지=%d",
        sido, sigungu, saved_count, duplicate_count, created_count,
    )

    return saved_count, duplicate_count, created_count


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
        saved, duplicates, created = save_transactions(
            db, transactions, sido, sigungu,
        )

        return {
            "sido": sido,
            "sigungu": sigungu,
            "deal_ymd": deal_ymd,
            "fetched": len(transactions),
            "saved": saved,
            "duplicates": duplicates,
            "unmatched": 0,
            "created": created,
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
