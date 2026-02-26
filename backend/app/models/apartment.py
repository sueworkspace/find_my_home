from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from app.models.database import Base


class ApartmentComplex(Base):
    """아파트 단지"""
    __tablename__ = "apartment_complex"

    id = Column(Integer, primary_key=True, autoincrement=True)
    naver_complex_no = Column(String(20), unique=True, nullable=True, index=True)  # 레거시 (nullable)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    sido = Column(String(20), nullable=False, index=True)
    sigungu = Column(String(20), nullable=False, index=True)
    dong = Column(String(20))
    dong_code = Column(String(10))  # 법정동코드 10자리 (KB시세 조회에 사용)
    total_units = Column(Integer)
    built_year = Column(Integer)
    lat = Column(Float)
    lng = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class KBPrice(Base):
    """KB 시세"""
    __tablename__ = "kb_price"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complex_id = Column(Integer, ForeignKey("apartment_complex.id"), nullable=False, index=True)
    area_sqm = Column(Float, nullable=False)
    price_lower = Column(BigInteger)
    price_mid = Column(BigInteger)
    price_upper = Column(BigInteger)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("complex_id", "area_sqm", name="uq_kb_price_complex_area"),
    )


class RealTransaction(Base):
    """실거래가"""
    __tablename__ = "real_transaction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complex_id = Column(Integer, ForeignKey("apartment_complex.id"), nullable=False, index=True)
    area_sqm = Column(Float, nullable=False)
    floor = Column(Integer)
    deal_price = Column(BigInteger, nullable=False)
    deal_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class ComplexComparison(Base):
    """단지별 KB시세 vs 최근 실거래가 비교"""
    __tablename__ = "complex_comparison"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complex_id = Column(Integer, ForeignKey("apartment_complex.id"), nullable=False, index=True)
    area_sqm = Column(Float, nullable=False)
    kb_price_mid = Column(BigInteger)          # KB시세 중간값
    recent_deal_price = Column(BigInteger)      # 최근 실거래가
    recent_deal_date = Column(DateTime)         # 최근 실거래일
    deal_discount_rate = Column(Float)          # 할인율: (KB - 실거래가) / KB * 100 (양수=KB보다 낮게 거래)
    deal_count_3m = Column(Integer, default=0)  # 최근 3개월 거래 건수
    compared_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("complex_id", "area_sqm", name="uq_complex_comparison"),
    )
