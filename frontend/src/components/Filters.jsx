/**
 * Filters 컴포넌트
 *
 * 역할:
 * - 매물 목록 필터링 (할인율, 호가, 면적)
 * - 접기/펼치기 토글 지원 (모바일에서 기본 접힌 상태)
 * - 활성 필터 표시 뱃지 및 총 건수/필터 건수 표시
 * - 필터 초기화 기능
 *
 * Props:
 * - filters: 현재 필터 상태 객체
 * - onFilterChange: 필터 변경 콜백
 * - totalCount: 전체 매물 수
 * - filteredCount: 필터 적용 후 매물 수
 */
import { useState, useEffect } from 'react';
import './Filters.css';

/** 할인율 옵션 목록 */
const DISCOUNT_OPTIONS = [
  { label: '전체', value: 0 },
  { label: '3% 이상', value: 3 },
  { label: '5% 이상', value: 5 },
  { label: '7% 이상', value: 7 },
  { label: '10% 이상', value: 10 },
];

/** 호가(매도 희망가) 옵션 목록 (단위: 만원) */
const PRICE_OPTIONS = [
  { label: '전체', min: 0, max: Infinity },
  { label: '5억 이하', min: 0, max: 50000 },
  { label: '5억 ~ 10억', min: 50000, max: 100000 },
  { label: '10억 ~ 15억', min: 100000, max: 150000 },
  { label: '15억 ~ 20억', min: 150000, max: 200000 },
  { label: '20억 ~ 30억', min: 200000, max: 300000 },
  { label: '30억 이상', min: 300000, max: Infinity },
];

/** 면적(평형) 옵션 목록 */
const AREA_OPTIONS = [
  { label: '전체', min: 0, max: Infinity },
  { label: '20평 미만', min: 0, max: 20 },
  { label: '20평 ~ 25평', min: 20, max: 25 },
  { label: '25평 ~ 35평', min: 25, max: 35 },
  { label: '35평 ~ 45평', min: 35, max: 45 },
  { label: '45평 이상', min: 45, max: Infinity },
];

/** 거래일 기간 필터 옵션 (개월 수, 0=전체) */
const DATE_OPTIONS = [
  { label: '전체', months: 0 },
  { label: '최근 1개월', months: 1 },
  { label: '최근 3개월', months: 3 },
  { label: '최근 6개월', months: 6 },
  { label: '최근 1년', months: 12 },
];

export default function Filters({ filters, onFilterChange, totalCount, filteredCount }) {
  /**
   * 필터 패널 열림/닫힘 상태
   * - 모바일(768px 미만)에서는 기본 닫힘
   * - 데스크톱에서는 기본 열림
   */
  const [isOpen, setIsOpen] = useState(() => window.innerWidth >= 768);

  /** 화면 크기 변경 시 데스크톱이면 패널 자동 열기 */
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        setIsOpen(true);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  /** 급매만 보기 토글 핸들러 */
  const handleBargainToggle = () => {
    const newBargainOnly = !filters.bargainOnly;
    onFilterChange({
      ...filters,
      bargainOnly: newBargainOnly,
      // 급매 토글 켜면 최소 할인율을 0으로 설정 (급매 = discountRate > 0)
      // 급매 토글 끄면 최소 할인율 필터도 초기화
      minDiscount: newBargainOnly ? (filters.minDiscount || 0) : 0,
    });
  };

  /** 최소 할인율 슬라이더 변경 핸들러 */
  const handleMinDiscountSlider = (e) => {
    onFilterChange({ ...filters, minDiscountValue: Number(e.target.value) });
  };

  /** 할인율 필터 변경 */
  const handleDiscountChange = (e) => {
    onFilterChange({ ...filters, minDiscount: Number(e.target.value) });
  };

  /** 호가 필터 변경 - 인덱스로 옵션 참조 */
  const handlePriceChange = (e) => {
    const idx = Number(e.target.value);
    const option = PRICE_OPTIONS[idx];
    onFilterChange({
      ...filters,
      priceMin: option.min,
      priceMax: option.max,
      priceIndex: idx,
    });
  };

  /** 면적 필터 변경 - 인덱스로 옵션 참조 */
  const handleAreaChange = (e) => {
    const idx = Number(e.target.value);
    const option = AREA_OPTIONS[idx];
    onFilterChange({
      ...filters,
      areaMin: option.min,
      areaMax: option.max,
      areaIndex: idx,
    });
  };

  /** 거래일 필터 변경 - 인덱스로 옵션 참조 */
  const handleDateChange = (e) => {
    const idx = Number(e.target.value);
    const option = DATE_OPTIONS[idx];
    onFilterChange({
      ...filters,
      dateMonths: option.months,
      dateIndex: idx,
    });
  };

  /** 모든 필터를 초기값으로 리셋 */
  const handleReset = () => {
    onFilterChange({
      minDiscount: 0,
      priceMin: 0,
      priceMax: Infinity,
      priceIndex: 0,
      areaMin: 0,
      areaMax: Infinity,
      areaIndex: 0,
      bargainOnly: false,
      minDiscountValue: 0,
      dateMonths: 0,
      dateIndex: 0,
    });
  };

  /** 현재 활성화된 필터가 있는지 확인 */
  const hasActiveFilter =
    filters.minDiscount > 0 || filters.priceIndex > 0 || filters.areaIndex > 0 ||
    filters.bargainOnly || filters.minDiscountValue > 0 || (filters.dateIndex || 0) > 0;

  return (
    <div className="filters">
      {/* 필터 헤더: 토글 버튼 + 건수 표시 */}
      <div className="filters__header">
        <button
          className="filters__toggle"
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
          aria-label="필터 패널 열기/닫기"
        >
          {/* 접기/펼치기 화살표 아이콘 */}
          <svg
            className={`filters__chevron ${isOpen ? 'filters__chevron--open' : ''}`}
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M4 6L8 10L12 6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="filters__title">필터</span>
          {/* 필터 활성 뱃지 */}
          {hasActiveFilter && <span className="filters__badge">적용중</span>}
        </button>

        {/* 매물 건수 표시 */}
        <div className="filters__counts">
          {filteredCount !== undefined && totalCount !== undefined && (
            <span className="filters__count-text">
              {filteredCount === totalCount
                ? `총 ${totalCount}건`
                : `${filteredCount}건 / ${totalCount}건`}
            </span>
          )}
        </div>
      </div>

      {/* 필터 본문: 토글 상태에 따라 표시/숨김 */}
      {isOpen && (
        <div className="filters__body">
          {/* 급매만 보기 토글 영역 */}
          <div className="filters__bargain-section">
            <div className="filters__bargain-toggle">
              <label className="filters__toggle-label" htmlFor="bargain-toggle">
                <span className="filters__toggle-text">급매만 보기</span>
                <span className="filters__toggle-desc">KB시세보다 저렴한 매물</span>
              </label>
              <button
                id="bargain-toggle"
                role="switch"
                aria-checked={filters.bargainOnly || false}
                className={`filters__switch ${filters.bargainOnly ? 'filters__switch--active' : ''}`}
                onClick={handleBargainToggle}
                aria-label="급매만 보기 토글"
              >
                <span className="filters__switch-knob" />
              </button>
            </div>

            {/* 급매 토글 활성 시: 최소 할인율 슬라이더 표시 */}
            {filters.bargainOnly && (
              <div className="filters__bargain-slider">
                <label className="filters__slider-label">
                  최소 할인율:
                  <strong className="filters__slider-value">
                    {filters.minDiscountValue || 0}%
                  </strong>
                </label>
                <input
                  type="range"
                  className="filters__range"
                  min="0"
                  max="20"
                  step="1"
                  value={filters.minDiscountValue || 0}
                  onChange={handleMinDiscountSlider}
                  aria-label="최소 할인율 슬라이더"
                />
                <div className="filters__range-labels">
                  <span>0%</span>
                  <span>5%</span>
                  <span>10%</span>
                  <span>15%</span>
                  <span>20%</span>
                </div>
              </div>
            )}
          </div>

          <div className="filters__row">
            {/* 할인율 필터 */}
            <div className="filters__group">
              <label className="filters__label">할인율</label>
              <select
                className="filters__select"
                value={filters.minDiscount}
                onChange={handleDiscountChange}
              >
                {DISCOUNT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 호가 필터 */}
            <div className="filters__group">
              <label className="filters__label">호가</label>
              <select
                className="filters__select"
                value={filters.priceIndex}
                onChange={handlePriceChange}
              >
                {PRICE_OPTIONS.map((opt, idx) => (
                  <option key={idx} value={idx}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 면적 필터 */}
            <div className="filters__group">
              <label className="filters__label">면적(평형)</label>
              <select
                className="filters__select"
                value={filters.areaIndex}
                onChange={handleAreaChange}
              >
                {AREA_OPTIONS.map((opt, idx) => (
                  <option key={idx} value={idx}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 거래일 필터 */}
            <div className="filters__group">
              <label className="filters__label">거래일</label>
              <select
                className="filters__select"
                value={filters.dateIndex || 0}
                onChange={handleDateChange}
              >
                {DATE_OPTIONS.map((opt, idx) => (
                  <option key={idx} value={idx}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* 필터 초기화 버튼: 활성 필터가 있을 때만 표시 */}
            {hasActiveFilter && (
              <button className="filters__reset" onClick={handleReset}>
                필터 초기화
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
