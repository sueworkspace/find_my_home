/**
 * Filters 컴포넌트
 *
 * 역할:
 * - 매물 목록 필터링 (급매, 할인율, 호가, 면적, 거래일)
 * - 직방/토스 스타일 가로 스크롤 칩 필터
 * - 각 칩 탭 시 다음 옵션으로 순환 (사이클 방식)
 * - 활성 칩: Toss blue 채운 스타일 / 비활성: 흰색 테두리 스타일
 * - Tailwind CSS 기반, CSS 파일 없음
 *
 * Props:
 * - filters: 현재 필터 상태 객체
 * - onFilterChange: 필터 변경 콜백
 * - totalCount: 전체 매물 수
 * - filteredCount: 필터 적용 후 매물 수
 */
import { cn } from '@/lib/utils';

/** 할인율 옵션 목록 */
const DISCOUNT_OPTIONS = [
  { label: '할인율', value: 0 },
  { label: '할인 3%↑', value: 3 },
  { label: '할인 5%↑', value: 5 },
  { label: '할인 7%↑', value: 7 },
  { label: '할인 10%↑', value: 10 },
];

/** 호가(매도 희망가) 옵션 목록 (단위: 만원) */
const PRICE_OPTIONS = [
  { label: '가격', min: 0, max: Infinity },
  { label: '5억 이하', min: 0, max: 50000 },
  { label: '5~10억', min: 50000, max: 100000 },
  { label: '10~15억', min: 100000, max: 150000 },
  { label: '15~20억', min: 150000, max: 200000 },
  { label: '20~30억', min: 200000, max: 300000 },
  { label: '30억↑', min: 300000, max: Infinity },
];

/** 면적(평형) 옵션 목록 */
const AREA_OPTIONS = [
  { label: '면적', min: 0, max: Infinity },
  { label: '20평 미만', min: 0, max: 20 },
  { label: '20~25평', min: 20, max: 25 },
  { label: '25~35평', min: 25, max: 35 },
  { label: '35~45평', min: 35, max: 45 },
  { label: '45평↑', min: 45, max: Infinity },
];

/** 거래일 기간 필터 옵션 (개월 수, 0=전체) */
const DATE_OPTIONS = [
  { label: '거래일', months: 0 },
  { label: '1개월', months: 1 },
  { label: '3개월', months: 3 },
  { label: '6개월', months: 6 },
  { label: '1년', months: 12 },
];

export default function Filters({ filters, onFilterChange, totalCount, filteredCount }) {
  /** 급매만 보기 토글 */
  const handleBargainToggle = () => {
    onFilterChange({
      ...filters,
      bargainOnly: !filters.bargainOnly,
      minDiscount: !filters.bargainOnly ? (filters.minDiscount || 0) : 0,
    });
  };

  /** 할인율 칩 탭 — 다음 옵션으로 순환 */
  const handleDiscountCycle = () => {
    const currentIdx = DISCOUNT_OPTIONS.findIndex(o => o.value === filters.minDiscount);
    const nextIdx = (currentIdx + 1) % DISCOUNT_OPTIONS.length;
    onFilterChange({ ...filters, minDiscount: DISCOUNT_OPTIONS[nextIdx].value });
  };

  /** 호가 칩 탭 — 다음 옵션으로 순환 */
  const handlePriceCycle = () => {
    const nextIdx = ((filters.priceIndex || 0) + 1) % PRICE_OPTIONS.length;
    const option = PRICE_OPTIONS[nextIdx];
    onFilterChange({ ...filters, priceMin: option.min, priceMax: option.max, priceIndex: nextIdx });
  };

  /** 면적 칩 탭 — 다음 옵션으로 순환 */
  const handleAreaCycle = () => {
    const nextIdx = ((filters.areaIndex || 0) + 1) % AREA_OPTIONS.length;
    const option = AREA_OPTIONS[nextIdx];
    onFilterChange({ ...filters, areaMin: option.min, areaMax: option.max, areaIndex: nextIdx });
  };

  /** 거래일 칩 탭 — 다음 옵션으로 순환 */
  const handleDateCycle = () => {
    const nextIdx = ((filters.dateIndex || 0) + 1) % DATE_OPTIONS.length;
    const option = DATE_OPTIONS[nextIdx];
    onFilterChange({ ...filters, dateMonths: option.months, dateIndex: nextIdx });
  };

  /** 모든 필터 초기화 */
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

  /* 현재 선택된 칩 라벨 계산 */
  const discountLabel = DISCOUNT_OPTIONS.find(o => o.value === filters.minDiscount)?.label ?? '할인율';
  const priceLabel = PRICE_OPTIONS[filters.priceIndex || 0]?.label ?? '가격';
  const areaLabel = AREA_OPTIONS[filters.areaIndex || 0]?.label ?? '면적';
  const dateLabel = DATE_OPTIONS[filters.dateIndex || 0]?.label ?? '거래일';

  /* 필터가 기본값이 아닌지 확인 */
  const isDiscountActive = filters.minDiscount > 0;
  const isPriceActive = (filters.priceIndex || 0) > 0;
  const isAreaActive = (filters.areaIndex || 0) > 0;
  const isDateActive = (filters.dateIndex || 0) > 0;
  const hasActiveFilter = filters.bargainOnly || isDiscountActive || isPriceActive || isAreaActive || isDateActive;

  return (
    <div className="w-full">
      {/* 가로 스크롤 칩 행 */}
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-none py-1">

        {/* 급매만 보기 칩 (토글) */}
        <button
          role="switch"
          aria-checked={filters.bargainOnly || false}
          onClick={handleBargainToggle}
          className={cn(
            'flex items-center gap-1.5 shrink-0 h-9 px-4 rounded-full text-[13px] font-medium transition-all',
            filters.bargainOnly
              ? 'bg-[#1B64DA] text-white'
              : 'bg-white text-[#4E5968] border border-[#E5E8EB] hover:border-[#1B64DA] hover:text-[#1B64DA]'
          )}
        >
          {/* 급매 뱃지 아이콘 */}
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path
              d="M8 1L10.09 5.26L14.5 5.97L11.25 9.14L12.04 13.5L8 11.31L3.96 13.5L4.75 9.14L1.5 5.97L5.91 5.26L8 1Z"
              fill="currentColor"
            />
          </svg>
          급매만
        </button>

        {/* 할인율 칩 */}
        <button
          onClick={handleDiscountCycle}
          aria-label={`할인율 필터: 현재 ${discountLabel}`}
          className={cn(
            'flex items-center gap-1 shrink-0 h-9 px-4 rounded-full text-[13px] font-medium transition-all',
            isDiscountActive
              ? 'bg-[#1B64DA] text-white'
              : 'bg-white text-[#4E5968] border border-[#E5E8EB] hover:border-[#1B64DA] hover:text-[#1B64DA]'
          )}
        >
          {discountLabel}
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {/* 가격 칩 */}
        <button
          onClick={handlePriceCycle}
          aria-label={`가격 필터: 현재 ${priceLabel}`}
          className={cn(
            'flex items-center gap-1 shrink-0 h-9 px-4 rounded-full text-[13px] font-medium transition-all',
            isPriceActive
              ? 'bg-[#1B64DA] text-white'
              : 'bg-white text-[#4E5968] border border-[#E5E8EB] hover:border-[#1B64DA] hover:text-[#1B64DA]'
          )}
        >
          {priceLabel}
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {/* 면적 칩 */}
        <button
          onClick={handleAreaCycle}
          aria-label={`면적 필터: 현재 ${areaLabel}`}
          className={cn(
            'flex items-center gap-1 shrink-0 h-9 px-4 rounded-full text-[13px] font-medium transition-all',
            isAreaActive
              ? 'bg-[#1B64DA] text-white'
              : 'bg-white text-[#4E5968] border border-[#E5E8EB] hover:border-[#1B64DA] hover:text-[#1B64DA]'
          )}
        >
          {areaLabel}
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {/* 거래일 칩 */}
        <button
          onClick={handleDateCycle}
          aria-label={`거래일 필터: 현재 ${dateLabel}`}
          className={cn(
            'flex items-center gap-1 shrink-0 h-9 px-4 rounded-full text-[13px] font-medium transition-all',
            isDateActive
              ? 'bg-[#1B64DA] text-white'
              : 'bg-white text-[#4E5968] border border-[#E5E8EB] hover:border-[#1B64DA] hover:text-[#1B64DA]'
          )}
        >
          {dateLabel}
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        {/* 구분선 */}
        {hasActiveFilter && (
          <div className="shrink-0 w-px h-5 bg-[#E5E8EB]" aria-hidden="true" />
        )}

        {/* 초기화 칩 — 활성 필터가 있을 때만 표시 */}
        {hasActiveFilter && (
          <button
            onClick={handleReset}
            aria-label="모든 필터 초기화"
            className="flex items-center gap-1 shrink-0 h-9 px-3 rounded-full text-[13px] font-medium text-[#8B95A1] border border-[#E5E8EB] hover:text-[#F04251] hover:border-[#F04251] transition-all"
          >
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            초기화
          </button>
        )}

        {/* 건수 표시 (오른쪽 끝, 밀려나지 않게 ml-auto) */}
        {filteredCount !== undefined && totalCount !== undefined && (
          <span className="ml-auto shrink-0 text-[13px] text-[#8B95A1] whitespace-nowrap">
            {filteredCount === totalCount
              ? `${totalCount}건`
              : `${filteredCount} / ${totalCount}건`}
          </span>
        )}
      </div>
    </div>
  );
}
