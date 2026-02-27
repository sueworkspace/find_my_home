/**
 * ComplexTable 컴포넌트
 *
 * KB시세 vs 실거래가 비교 단지 목록을 테이블/카드로 렌더링합니다.
 * - 할인율: 절대값(억 단위) +/- 표시 (음수 = KB보다 낮게 거래 = 급매 = 빨강)
 * - 실거래일 표시 (YYYY.MM.DD)
 * - 모바일: 카드 형태 + 드롭다운 정렬, 데스크톱: 테이블 형태 + 헤더 클릭 정렬
 * - 정렬 가능 컬럼: 실거래가, KB시세, 차이, 거래일
 * - 기본 정렬: 거래일 최신순
 *
 * 스타일: Tailwind CSS + shadcn/ui Card, Badge (ComplexTable.css 제거됨)
 */
import { useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

/**
 * 만원 → 모바일 축약 표기 (12.3억 / 9,500만)
 * compact=true 이면 "12.3억" 형태, false 이면 "12억 3,000만" 형태
 */
function formatPrice(manwon, compact = false) {
  if (manwon == null) return '-';
  if (manwon >= 10000) {
    const eok = manwon / 10000;
    if (compact) return `${eok % 1 === 0 ? eok : eok.toFixed(1)}억`;
    const eokInt = Math.floor(eok);
    const rem = manwon % 10000;
    return rem > 0 ? `${eokInt}억 ${rem.toLocaleString()}만` : `${eokInt}억`;
  }
  return `${manwon.toLocaleString()}만`;
}

/** m² → 평형 변환 */
function sqmToPyeong(sqm) {
  return Math.round(sqm / 3.3058);
}

/**
 * 시세 차이 뱃지 (억 단위, +/- 부호)
 * 실거래가 - KB시세 기준:
 *   음수(급매, 실거래가 < KB시세) → 빨강 뱃지 (#F04251 on #FFF3F4)
 *   양수(프리미엄, 실거래가 > KB시세) → 파랑 뱃지 (#3182F6 on #EBF3FF)
 *   0 → 회색 뱃지
 */
function DiffBadge({ kbPrice, dealPrice }) {
  if (kbPrice == null || dealPrice == null) return <span className="text-[#8B95A1]">-</span>;

  const diff = dealPrice - kbPrice; // 만원 단위, 음수=급매, 양수=프리미엄
  const isPositive = diff > 0;
  const absDiff = Math.abs(diff);

  /* 억 단위 표기 */
  let label;
  if (absDiff >= 10000) {
    const eok = absDiff / 10000;
    const numStr = eok % 1 === 0 ? String(eok) : eok.toFixed(1);
    label = isPositive ? `+${numStr}억` : `-${numStr}억`;
  } else if (absDiff > 0) {
    label = isPositive ? `+${absDiff.toLocaleString()}만` : `-${absDiff.toLocaleString()}만`;
  } else {
    return (
      <Badge
        className="bg-[#F2F4F6] text-[#8B95A1] border-0 font-bold text-[12px] px-2 py-0.5 rounded-md"
      >
        0
      </Badge>
    );
  }

  const tooltip = isPositive
    ? `KB시세보다 ${formatPrice(absDiff)} 높게 거래 (프리미엄)`
    : `KB시세보다 ${formatPrice(absDiff)} 낮게 거래 (급매)`;

  return (
    <Badge
      title={tooltip}
      className={cn(
        'border-0 font-bold text-[12px] px-2 py-0.5 rounded-md whitespace-nowrap',
        isPositive
          ? 'bg-[#EBF3FF] text-[#3182F6]'   // 프리미엄: 파랑
          : 'bg-[#FFF3F4] text-[#F04251]',   // 급매: 빨강
      )}
    >
      {label}
    </Badge>
  );
}

/** 날짜 포맷 (YYYY.MM.DD) */
function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '-';
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}.${m}.${day}`;
}

/** 모바일 정렬 옵션 목록 */
const SORT_OPTIONS_MOBILE = [
  { key: 'recentDealDate',    direction: 'desc', label: '거래일 최신순' },
  { key: 'dealDiscountRate',  direction: 'desc', label: '할인 큰순' },
  { key: 'dealDiscountRate',  direction: 'asc',  label: '할인 작은순' },
  { key: 'recentDealPrice',   direction: 'asc',  label: '실거래가 낮은순' },
  { key: 'recentDealPrice',   direction: 'desc', label: '실거래가 높은순' },
  { key: 'kbPriceMid',        direction: 'asc',  label: 'KB시세 낮은순' },
  { key: 'kbPriceMid',        direction: 'desc', label: 'KB시세 높은순' },
];

/** 정렬 화살표 아이콘 */
function SortArrow({ active, direction }) {
  return (
    <span
      className={cn(
        'ml-1 inline-block text-[10px] transition-opacity',
        active ? 'opacity-100' : 'opacity-0 group-hover:opacity-40',
      )}
    >
      {direction === 'asc' ? '▲' : '▼'}
    </span>
  );
}

export default function ComplexTable({ complexes }) {
  /* 정렬 상태: 기본 거래일 최신순 */
  const [sortConfig, setSortConfig] = useState({ key: 'recentDealDate', direction: 'desc' });

  /**
   * 정렬된 단지 목록
   * - null 값은 항상 맨 뒤로 배치
   * - 날짜 정렬은 문자열 비교로 처리
   */
  const sortedComplexes = useMemo(() => {
    if (!complexes || complexes.length === 0) return [];

    return [...complexes].sort((a, b) => {
      const va = a[sortConfig.key];
      const vb = b[sortConfig.key];

      /* null 값 처리: 항상 맨 뒤 */
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;

      /* 날짜 문자열은 문자열 비교 */
      let cmp;
      if (sortConfig.key === 'recentDealDate') {
        cmp = String(va).localeCompare(String(vb));
      } else {
        cmp = va - vb;
      }
      return sortConfig.direction === 'asc' ? cmp : -cmp;
    });
  }, [complexes, sortConfig]);

  /** 데스크톱 헤더 클릭 정렬 토글 */
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  };

  /** 모바일 드롭다운 정렬 변경 */
  const handleMobileSortChange = (e) => {
    const idx = Number(e.target.value);
    const option = SORT_OPTIONS_MOBILE[idx];
    setSortConfig({ key: option.key, direction: option.direction });
  };

  /** 현재 선택된 모바일 정렬 옵션 인덱스 */
  const currentMobileSortIndex = SORT_OPTIONS_MOBILE.findIndex(
    opt => opt.key === sortConfig.key && opt.direction === sortConfig.direction,
  );

  /* ── 빈 상태 ── */
  if (!complexes || complexes.length === 0) {
    return (
      <div className="flex items-center justify-center py-10 text-[14px] text-[#8B95A1]">
        비교 데이터가 없습니다. KB시세와 실거래가가 모두 수집된 단지만 표시됩니다.
      </div>
    );
  }

  return (
    <div className="w-full">

      {/* ── 모바일 정렬 드롭다운 (767px 이하) ── */}
      <div className="flex items-center gap-2 mb-2 md:hidden">
        <span className="text-[13px] font-semibold text-[#8B95A1]">정렬</span>
        <select
          className="flex-1 bg-white rounded-xl border-0 shadow-sm text-[14px] text-[#191F28] px-3 py-2 pr-8 appearance-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-brand)]/20 bg-[url('data:image/svg+xml,%3Csvg%20xmlns=%27http://www.w3.org/2000/svg%27%20width=%2712%27%20height=%2712%27%20viewBox=%270%200%2012%2012%27%3E%3Cpath%20fill=%27%238B95A1%27%20d=%27M2.5%204.5L6%208l3.5-3.5%27/%3E%3C/svg%3E')] bg-no-repeat bg-[right_12px_center] bg-[length:12px]"
          value={currentMobileSortIndex >= 0 ? currentMobileSortIndex : 0}
          onChange={handleMobileSortChange}
          aria-label="정렬 기준 선택"
        >
          {SORT_OPTIONS_MOBILE.map((opt, idx) => (
            <option key={idx} value={idx}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* ── 데스크톱 테이블 (768px 이상) ── */}
      <div className="hidden md:block overflow-x-auto rounded-2xl shadow-sm bg-white">
        <table className="w-full border-collapse text-[14px]">
          <thead>
            <tr className="bg-[#F9FAFB]">
              <th className="px-4 py-3 text-left text-[13px] font-semibold text-[#8B95A1] border-b border-[#F2F4F6] whitespace-nowrap">
                아파트명
              </th>
              <th className="px-4 py-3 text-left text-[13px] font-semibold text-[#8B95A1] border-b border-[#F2F4F6] whitespace-nowrap">
                지역
              </th>
              <th className="px-4 py-3 text-left text-[13px] font-semibold text-[#8B95A1] border-b border-[#F2F4F6] whitespace-nowrap">
                면적
              </th>
              {/* 실거래가 */}
              <th
                className="group px-4 py-3 text-right text-[13px] font-semibold text-[#8B95A1] border-b border-[#F2F4F6] whitespace-nowrap cursor-pointer select-none hover:bg-[#F2F4F6] transition-colors"
                onClick={() => handleSort('recentDealPrice')}
              >
                실거래가
                <SortArrow
                  active={sortConfig.key === 'recentDealPrice'}
                  direction={sortConfig.key === 'recentDealPrice' ? sortConfig.direction : 'desc'}
                />
              </th>
              {/* KB시세 */}
              <th
                className="group px-4 py-3 text-right text-[13px] font-semibold text-[#8B95A1] border-b border-[#F2F4F6] whitespace-nowrap cursor-pointer select-none hover:bg-[#F2F4F6] transition-colors"
                onClick={() => handleSort('kbPriceMid')}
              >
                KB시세
                <SortArrow
                  active={sortConfig.key === 'kbPriceMid'}
                  direction={sortConfig.key === 'kbPriceMid' ? sortConfig.direction : 'desc'}
                />
              </th>
              {/* 차이 */}
              <th
                className="group px-4 py-3 text-center text-[13px] font-semibold text-[#8B95A1] border-b border-[#F2F4F6] whitespace-nowrap cursor-pointer select-none hover:bg-[#F2F4F6] transition-colors"
                onClick={() => handleSort('dealDiscountRate')}
              >
                차이
                <SortArrow
                  active={sortConfig.key === 'dealDiscountRate'}
                  direction={sortConfig.key === 'dealDiscountRate' ? sortConfig.direction : 'desc'}
                />
              </th>
              {/* 거래일 */}
              <th
                className="group px-4 py-3 text-center text-[13px] font-semibold text-[#8B95A1] border-b border-[#F2F4F6] whitespace-nowrap cursor-pointer select-none hover:bg-[#F2F4F6] transition-colors"
                onClick={() => handleSort('recentDealDate')}
              >
                거래일
                <SortArrow
                  active={sortConfig.key === 'recentDealDate'}
                  direction={sortConfig.key === 'recentDealDate' ? sortConfig.direction : 'desc'}
                />
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedComplexes.map((item, idx) => (
              <tr
                key={`${item.complexId}-${item.areaSqm}-${idx}`}
                className="border-b border-[#F2F4F6] hover:bg-[#F9FAFB] transition-colors last:border-0"
              >
                {/* 아파트명 */}
                <td className="px-4 py-3 align-middle">
                  <span className="font-medium text-[#191F28]">{item.name}</span>
                  <span className="block text-[12px] text-[#8B95A1] mt-0.5">
                    {item.builtYear ? `${item.builtYear}년` : ''}
                    {item.builtYear && item.totalUnits ? ' · ' : ''}
                    {item.totalUnits ? `${item.totalUnits.toLocaleString()}세대` : ''}
                  </span>
                </td>
                {/* 지역 */}
                <td className="px-4 py-3 align-middle text-[#191F28]">
                  <span>{item.sigungu}</span>
                  {item.dong && (
                    <span className="text-[#8B95A1] text-[13px]"> {item.dong}</span>
                  )}
                </td>
                {/* 면적 */}
                <td className="px-4 py-3 align-middle whitespace-nowrap text-[#191F28]">
                  {item.areaSqm.toFixed(1)}㎡
                  <span className="text-[#8B95A1] text-[12px] ml-0.5">({sqmToPyeong(item.areaSqm)}평)</span>
                </td>
                {/* 실거래가 */}
                <td className="px-4 py-3 align-middle text-right whitespace-nowrap font-bold text-[#191F28]">
                  {formatPrice(item.recentDealPrice)}
                </td>
                {/* KB시세 */}
                <td className="px-4 py-3 align-middle text-right whitespace-nowrap font-bold text-[#191F28]">
                  {formatPrice(item.kbPriceMid)}
                </td>
                {/* 차이 */}
                <td className="px-4 py-3 align-middle text-center">
                  <DiffBadge kbPrice={item.kbPriceMid} dealPrice={item.recentDealPrice} />
                </td>
                {/* 거래일 */}
                <td className="px-4 py-3 align-middle text-center whitespace-nowrap text-[#8B95A1] text-[13px]">
                  {formatDate(item.recentDealDate)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── 모바일 카드 레이아웃 (767px 이하) ── */}
      <div className="flex flex-col gap-2 md:hidden">
        {sortedComplexes.map((item, idx) => (
          <article
            key={`card-${item.complexId}-${item.areaSqm}-${idx}`}
            className="bg-white rounded-2xl shadow-sm border-0 p-5"
          >
            {/* 헤더: 단지명 + 차이 뱃지 */}
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-[15px] text-[#191F28] leading-snug">
                {item.name}
              </span>
              <DiffBadge kbPrice={item.kbPriceMid} dealPrice={item.recentDealPrice} />
            </div>

            {/* 서브 정보: 지역 · 면적 · 연도 · 세대수 */}
            <div className="flex items-center flex-wrap gap-1.5 mb-3 text-[13px] text-[#8B95A1]">
              <span>{item.sigungu}{item.dong ? ` ${item.dong}` : ''}</span>
              <span className="inline-block w-1 h-1 rounded-full bg-[#D1D5DB]" aria-hidden="true" />
              <span>{item.areaSqm.toFixed(1)}㎡({sqmToPyeong(item.areaSqm)}평)</span>
              {item.builtYear && (
                <>
                  <span className="inline-block w-1 h-1 rounded-full bg-[#D1D5DB]" aria-hidden="true" />
                  <span>{item.builtYear}년</span>
                </>
              )}
              {item.totalUnits && (
                <>
                  <span className="inline-block w-1 h-1 rounded-full bg-[#D1D5DB]" aria-hidden="true" />
                  <span>{item.totalUnits.toLocaleString()}세대</span>
                </>
              )}
            </div>

            {/* 가격 행 */}
            <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[#F2F4F6]">
              <div className="flex flex-col items-center gap-1">
                <span className="text-[13px] text-[#8B95A1]">실거래가</span>
                <span className="font-bold text-[15px] text-[#191F28]">
                  {formatPrice(item.recentDealPrice, true)}
                </span>
              </div>
              <div className="flex flex-col items-center gap-1">
                <span className="text-[13px] text-[#8B95A1]">KB시세</span>
                <span className="font-bold text-[15px] text-[#191F28]">
                  {formatPrice(item.kbPriceMid, true)}
                </span>
              </div>
              <div className="flex flex-col items-center gap-1">
                <span className="text-[13px] text-[#8B95A1]">거래일</span>
                <span className="font-medium text-[14px] text-[#8B95A1]">
                  {formatDate(item.recentDealDate)}
                </span>
              </div>
            </div>
          </article>
        ))}
      </div>

    </div>
  );
}
