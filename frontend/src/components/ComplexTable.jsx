/**
 * ComplexTable 컴포넌트
 *
 * KB시세 vs 실거래가 비교 단지 목록을 테이블/카드로 렌더링합니다.
 * - 할인율: 절대값(억 단위) +/- 표시 (양수 = KB보다 낮게 거래 = 급매)
 * - 실거래일 표시 (YYYY.MM.DD)
 * - 모바일: 카드 형태 + 드롭다운 정렬, 데스크톱: 테이블 형태 + 헤더 클릭 정렬
 * - 정렬 가능 컬럼: 실거래가, KB시세, 할인율, 거래일
 * - 기본 정렬: 거래일 최신순
 */
import { useState, useMemo } from 'react';
import './ComplexTable.css';

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
 * 할인 금액 절대값 표시 (억 단위, +/- 부호)
 * KB시세 - 실거래가 = 양수면 급매(초록), 음수면 프리미엄(빨강)
 */
function DiffBadge({ kbPrice, dealPrice }) {
  if (kbPrice == null || dealPrice == null) return <span>-</span>;
  const diff = kbPrice - dealPrice; // 만원 단위, 양수=급매
  const isPositive = diff > 0;
  const cls = isPositive ? 'complex-table__badge--positive' : 'complex-table__badge--negative';
  const sign = isPositive ? '+' : '';

  /* 억 단위 표기 */
  const absDiff = Math.abs(diff);
  let label;
  if (absDiff >= 10000) {
    const eok = absDiff / 10000;
    label = `${sign}${isPositive ? '' : '-'}${eok % 1 === 0 ? eok : eok.toFixed(1)}억`;
  } else if (absDiff > 0) {
    label = `${sign}${isPositive ? '' : '-'}${absDiff.toLocaleString()}만`;
  } else {
    return <span className="complex-table__badge">0</span>;
  }

  const tooltip = isPositive
    ? `KB시세보다 ${formatPrice(absDiff)} 낮게 거래`
    : `KB시세보다 ${formatPrice(absDiff)} 높게 거래`;

  return (
    <span className={`complex-table__badge ${cls}`} title={tooltip}>
      {label}
    </span>
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
  { key: 'recentDealDate', direction: 'desc', label: '거래일 최신순' },
  { key: 'dealDiscountRate', direction: 'desc', label: '할인 큰순' },
  { key: 'dealDiscountRate', direction: 'asc', label: '할인 작은순' },
  { key: 'recentDealPrice', direction: 'asc', label: '실거래가 낮은순' },
  { key: 'recentDealPrice', direction: 'desc', label: '실거래가 높은순' },
  { key: 'kbPriceMid', direction: 'asc', label: 'KB시세 낮은순' },
  { key: 'kbPriceMid', direction: 'desc', label: 'KB시세 높은순' },
];

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

  /** 정렬 화살표 표시 */
  const getSortIndicator = (key) => {
    if (sortConfig.key !== key) return null;
    return <span className="complex-table__sort-arrow">{sortConfig.direction === 'asc' ? '\u25B2' : '\u25BC'}</span>;
  };

  /** 현재 선택된 모바일 정렬 옵션 인덱스 */
  const currentMobileSortIndex = SORT_OPTIONS_MOBILE.findIndex(
    opt => opt.key === sortConfig.key && opt.direction === sortConfig.direction
  );

  if (!complexes || complexes.length === 0) {
    return (
      <div className="complex-table__empty">
        비교 데이터가 없습니다. KB시세와 실거래가가 모두 수집된 단지만 표시됩니다.
      </div>
    );
  }

  return (
    <div className="complex-table__wrapper">
      {/* 모바일 정렬 드롭다운 (768px 미만에서만 표시) */}
      <div className="complex-table__mobile-sort">
        <label className="complex-table__mobile-sort-label">정렬:</label>
        <select
          className="complex-table__mobile-sort-select"
          value={currentMobileSortIndex >= 0 ? currentMobileSortIndex : 0}
          onChange={handleMobileSortChange}
        >
          {SORT_OPTIONS_MOBILE.map((opt, idx) => (
            <option key={idx} value={idx}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* 데스크톱 테이블 (768px 이상에서만 표시) */}
      <div className="complex-table__desktop">
        <table className="complex-table">
          <thead>
            <tr>
              <th>아파트명</th>
              <th>지역</th>
              <th>면적</th>
              <th className="complex-table__sortable" onClick={() => handleSort('recentDealPrice')}>
                실거래가{getSortIndicator('recentDealPrice')}
              </th>
              <th className="complex-table__sortable" onClick={() => handleSort('kbPriceMid')}>
                KB시세{getSortIndicator('kbPriceMid')}
              </th>
              <th className="complex-table__sortable" onClick={() => handleSort('dealDiscountRate')}>
                차이{getSortIndicator('dealDiscountRate')}
              </th>
              <th className="complex-table__sortable" onClick={() => handleSort('recentDealDate')}>
                거래일{getSortIndicator('recentDealDate')}
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedComplexes.map((item, idx) => (
              <tr key={`${item.complexId}-${item.areaSqm}-${idx}`}>
                <td className="complex-table__name">
                  <span>{item.name}</span>
                  {item.builtYear && (
                    <span className="complex-table__year">{item.builtYear}년</span>
                  )}
                </td>
                <td className="complex-table__region">
                  <span>{item.sigungu}</span>
                  {item.dong && <span className="complex-table__dong"> {item.dong}</span>}
                </td>
                <td className="complex-table__area">
                  {item.areaSqm.toFixed(1)}㎡
                  <span className="complex-table__pyeong">({sqmToPyeong(item.areaSqm)}평)</span>
                </td>
                <td className="complex-table__price">
                  <span className="complex-table__price--full">{formatPrice(item.recentDealPrice)}</span>
                  <span className="complex-table__price--compact">{formatPrice(item.recentDealPrice, true)}</span>
                </td>
                <td className="complex-table__price">
                  <span className="complex-table__price--full">{formatPrice(item.kbPriceMid)}</span>
                  <span className="complex-table__price--compact">{formatPrice(item.kbPriceMid, true)}</span>
                </td>
                <td>
                  <DiffBadge kbPrice={item.kbPriceMid} dealPrice={item.recentDealPrice} />
                </td>
                <td className="complex-table__date">{formatDate(item.recentDealDate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 모바일 카드 레이아웃 (768px 미만에서만 표시) */}
      <div className="complex-table__cards">
        {sortedComplexes.map((item, idx) => (
          <article key={`card-${item.complexId}-${item.areaSqm}-${idx}`} className="complex-card">
            <div className="complex-card__header">
              <span className="complex-card__name">{item.name}</span>
              <DiffBadge kbPrice={item.kbPriceMid} dealPrice={item.recentDealPrice} />
            </div>
            <div className="complex-card__sub">
              <span>{item.sigungu}{item.dong ? ` ${item.dong}` : ''}</span>
              <span className="complex-card__dot" />
              <span>{item.areaSqm.toFixed(1)}㎡ ({sqmToPyeong(item.areaSqm)}평)</span>
              {item.builtYear && <span className="complex-card__dot" />}
              {item.builtYear && <span>{item.builtYear}년</span>}
            </div>
            <div className="complex-card__prices">
              <div className="complex-card__price-item">
                <span className="complex-card__price-label">실거래가</span>
                <span>{formatPrice(item.recentDealPrice, true)}</span>
              </div>
              <div className="complex-card__price-item">
                <span className="complex-card__price-label">KB시세</span>
                <span>{formatPrice(item.kbPriceMid, true)}</span>
              </div>
              <div className="complex-card__price-item">
                <span className="complex-card__price-label">거래일</span>
                <span>{formatDate(item.recentDealDate)}</span>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
