import { useState } from 'react';
import './Filters.css';

const DISCOUNT_OPTIONS = [
  { label: '전체', value: 0 },
  { label: '3% 이상', value: 3 },
  { label: '5% 이상', value: 5 },
  { label: '7% 이상', value: 7 },
  { label: '10% 이상', value: 10 },
];

const PRICE_OPTIONS = [
  { label: '전체', min: 0, max: Infinity },
  { label: '5억 이하', min: 0, max: 50000 },
  { label: '5억 ~ 10억', min: 50000, max: 100000 },
  { label: '10억 ~ 15억', min: 100000, max: 150000 },
  { label: '15억 ~ 20억', min: 150000, max: 200000 },
  { label: '20억 ~ 30억', min: 200000, max: 300000 },
  { label: '30억 이상', min: 300000, max: Infinity },
];

const AREA_OPTIONS = [
  { label: '전체', min: 0, max: Infinity },
  { label: '20평 미만', min: 0, max: 20 },
  { label: '20평 ~ 25평', min: 20, max: 25 },
  { label: '25평 ~ 35평', min: 25, max: 35 },
  { label: '35평 ~ 45평', min: 35, max: 45 },
  { label: '45평 이상', min: 45, max: Infinity },
];

export default function Filters({ filters, onFilterChange, totalCount, filteredCount }) {
  const [isOpen, setIsOpen] = useState(true);

  const handleDiscountChange = (e) => {
    onFilterChange({ ...filters, minDiscount: Number(e.target.value) });
  };

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

  const handleReset = () => {
    onFilterChange({
      minDiscount: 0,
      priceMin: 0,
      priceMax: Infinity,
      priceIndex: 0,
      areaMin: 0,
      areaMax: Infinity,
      areaIndex: 0,
    });
  };

  const hasActiveFilter =
    filters.minDiscount > 0 || filters.priceIndex > 0 || filters.areaIndex > 0;

  return (
    <div className="filters">
      <div className="filters__header">
        <button
          className="filters__toggle"
          onClick={() => setIsOpen(!isOpen)}
          aria-expanded={isOpen}
        >
          <svg
            className={`filters__chevron ${isOpen ? 'filters__chevron--open' : ''}`}
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
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
          {hasActiveFilter && <span className="filters__badge">적용중</span>}
        </button>
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

      {isOpen && (
        <div className="filters__body">
          <div className="filters__row">
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
