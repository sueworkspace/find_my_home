from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from app.models.database import Base


class ApartmentComplex(Base):
    """아파트 단지"""
    __tablename__ = "apartment_complex"

    id = Column(Integer, primary_key=True, autoincrement=True)
    naver_complex_no = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200))
    sido = Column(String(20), nullable=False, index=True)
    sigungu = Column(String(20), nullable=False, index=True)
    dong = Column(String(20))
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


class Listing(Base):
    """네이버 부동산 매물"""
    __tablename__ = "listing"

    id = Column(Integer, primary_key=True, autoincrement=True)
    naver_article_id = Column(String(20), unique=True, nullable=False, index=True)
    complex_id = Column(Integer, ForeignKey("apartment_complex.id"), nullable=False, index=True)
    dong = Column(String(20))
    area_sqm = Column(Float, nullable=False)
    floor = Column(Integer)
    asking_price = Column(BigInteger, nullable=False)
    listing_url = Column(String(500))
    registered_at = Column(DateTime)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PriceComparison(Base):
    """매물 호가 vs KB시세 비교"""
    __tablename__ = "price_comparison"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("listing.id"), nullable=False, index=True)
    kb_price_id = Column(Integer, ForeignKey("kb_price.id"), nullable=False)
    kb_mid_price = Column(BigInteger, nullable=False)
    asking_price = Column(BigInteger, nullable=False)
    price_diff = Column(BigInteger, nullable=False)
    discount_rate = Column(Float, nullable=False)
    compared_at = Column(DateTime, server_default=func.now())


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
