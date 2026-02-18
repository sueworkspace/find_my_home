/**
 * ListingsTable 컴포넌트
 *
 * 역할:
 * - 매물 목록을 테이블(데스크톱) 또는 카드(모바일) 형태로 표시
 * - 컬럼 클릭으로 정렬 기능 제공 (오름차순/내림차순 토글)
 * - 행 클릭 시 네이버 부동산 상세 페이지로 이동
 * - 할인율 뱃지 색상 구분 (양수/급매: 초록, 음수: 빨강, null: 회색)
 * - 급매 매물(discount_rate > 0) 행/카드에 초록 배경 강조 표시
 *
 * 반응형 전략:
 * - 모바일(768px 미만): 카드형 리스트 (가로 스크롤 없음)
 * - 데스크톱(768px 이상): 전통적인 테이블 레이아웃
 *
 * Props:
 * - listings: 표시할 매물 배열
 */
import { useState, useMemo } from 'react';
import { formatPrice, formatArea, formatDiscountRate, formatDate, formatFloor } from '../utils/format';
import './ListingsTable.css';

/** 테이블 컬럼 정의 (데스크톱에서 사용) */
const COLUMNS = [
  { key: 'apartmentName', label: '아파트명', sortable: true, align: 'left' },
  { key: 'dong', label: '동', sortable: true, align: 'center' },
  { key: 'areaPyeong', label: '평형', sortable: true, align: 'center' },
  { key: 'askingPrice', label: '호가', sortable: true, align: 'right' },
  { key: 'kbPrice', label: 'KB시세', sortable: true, align: 'right' },
  { key: 'discountRate', label: '할인율', sortable: true, align: 'center' },
  { key: 'floor', label: '층수', sortable: true, align: 'center' },
  { key: 'registeredAt', label: '등록일', sortable: true, align: 'center' },
  { key: 'recentDealPrice', label: '최근 실거래가', sortable: true, align: 'right' },
];

/** 모바일 정렬 옵션 (카드 뷰에서 사용) */
const SORT_OPTIONS = [
  { key: 'discountRate', direction: 'desc', label: '할인율 높은순' },
  { key: 'discountRate', direction: 'asc', label: '할인율 낮은순' },
  { key: 'askingPrice', direction: 'asc', label: '호가 낮은순' },
  { key: 'askingPrice', direction: 'desc', label: '호가 높은순' },
  { key: 'registeredAt', direction: 'desc', label: '최신 등록순' },
  { key: 'areaPyeong', direction: 'desc', label: '면적 넓은순' },
];

export default function ListingsTable({ listings }) {
  /** 현재 정렬 상태 (기본: 할인율 내림차순) */
  const [sortConfig, setSortConfig] = useState({ key: 'discountRate', direction: 'desc' });

  /**
   * 정렬된 매물 목록 (메모이제이션)
   * - null 값은 맨 뒤로 배치
   * - 문자열은 대소문자 무시 비교
   */
  const sortedListings = useMemo(() => {
    if (!listings || listings.length === 0) return [];

    const sorted = [...listings].sort((a, b) => {
      const { key, direction } = sortConfig;
      let aVal = a[key];
      let bVal = b[key];

      // null/undefined 처리: 항상 맨 뒤로
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      // 문자열 비교: 대소문자 무시
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }

      if (aVal < bVal) return direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return direction === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [listings, sortConfig]);

  /** 데스크톱 테이블 헤더 클릭 시 정렬 토글 */
  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  };

  /** 모바일 정렬 드롭다운 변경 핸들러 */
  const handleMobileSortChange = (e) => {
    const idx = Number(e.target.value);
    const option = SORT_OPTIONS[idx];
    setSortConfig({ key: option.key, direction: option.direction });
  };

  /** 정렬 인디케이터 CSS 클래스 반환 */
  const getSortIndicator = (key) => {
    if (sortConfig.key !== key) return 'sort-indicator sort-indicator--inactive';
    return `sort-indicator sort-indicator--${sortConfig.direction}`;
  };

  /** 행/카드 클릭 시 네이버 부동산 새 탭으로 열기 */
  const handleRowClick = (listing) => {
    if (listing.listingUrl) {
      window.open(listing.listingUrl, '_blank', 'noopener,noreferrer');
    }
  };

  /**
   * 할인율에 따른 CSS 클래스 반환
   * - 양수(KB시세보다 저렴 = 급매): 초록색
   * - 음수(KB시세보다 비쌈): 빨간색
   * - null/undefined: 회색
   */
  const getDiscountClass = (rate) => {
    if (rate == null) return 'listings-table__discount--null';
    if (rate > 0) return 'listings-table__discount--positive';
    if (rate < 0) return 'listings-table__discount--negative';
    return 'listings-table__discount--null';
  };

  /**
   * 급매 여부 판단 (discount_rate > 0이면 급매)
   * - KB시세보다 저렴한 매물을 급매로 판단
   */
  const isBargain = (listing) => {
    return listing.discountRate != null && listing.discountRate > 0;
  };

  /** 현재 선택된 모바일 정렬 옵션의 인덱스 */
  const currentSortIndex = SORT_OPTIONS.findIndex(
    (opt) => opt.key === sortConfig.key && opt.direction === sortConfig.direction
  );

  if (!listings || listings.length === 0) {
    return null;
  }

  return (
    <div className="listings-table-wrapper">
      {/* === 모바일 정렬 드롭다운 (768px 미만에서만 표시) === */}
      <div className="listings-table__mobile-sort">
        <label className="listings-table__mobile-sort-label">정렬</label>
        <select
          className="listings-table__mobile-sort-select"
          value={currentSortIndex >= 0 ? currentSortIndex : 0}
          onChange={handleMobileSortChange}
        >
          {SORT_OPTIONS.map((opt, idx) => (
            <option key={idx} value={idx}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* === 데스크톱 테이블 (768px 이상에서만 표시) === */}
      <div className="listings-table__desktop">
        <table className="listings-table">
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={`listings-table__th listings-table__th--${col.align}`}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  style={{ cursor: col.sortable ? 'pointer' : 'default' }}
                >
                  <span className="listings-table__th-content">
                    {col.label}
                    {col.sortable && (
                      <span className={getSortIndicator(col.key)}>
                        {sortConfig.key === col.key
                          ? sortConfig.direction === 'asc'
                            ? '\u25B2'
                            : '\u25BC'
                          : '\u25BC'}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedListings.map((listing) => (
              <tr
                key={listing.id}
                className={`listings-table__row ${isBargain(listing) ? 'listings-table__row--bargain' : ''}`}
                onClick={() => handleRowClick(listing)}
                title="클릭하면 네이버 부동산 상세 페이지로 이동합니다"
              >
                <td className="listings-table__td listings-table__td--left">
                  <span className="listings-table__apt-name">{listing.apartmentName}</span>
                </td>
                <td className="listings-table__td listings-table__td--center">
                  {listing.dong || '-'}
                </td>
                <td className="listings-table__td listings-table__td--center">
                  {formatArea(listing.areaSqm, listing.areaPyeong)}
                </td>
                <td className="listings-table__td listings-table__td--right listings-table__td--price">
                  {formatPrice(listing.askingPrice)}
                </td>
                <td className="listings-table__td listings-table__td--right listings-table__td--kb">
                  {listing.kbPrice ? formatPrice(listing.kbPrice) : '-'}
                </td>
                <td className="listings-table__td listings-table__td--center">
                  <span className={`listings-table__discount ${getDiscountClass(listing.discountRate)}`}>
                    {formatDiscountRate(listing.discountRate)}
                  </span>
                </td>
                <td className="listings-table__td listings-table__td--center">
                  {formatFloor(listing.floor)}
                </td>
                <td className="listings-table__td listings-table__td--center">
                  {formatDate(listing.registeredAt)}
                </td>
                <td className="listings-table__td listings-table__td--right">
                  <div className="listings-table__deal">
                    <span>{listing.recentDealPrice ? formatPrice(listing.recentDealPrice) : '-'}</span>
                    {listing.recentDealDate && (
                      <span className="listings-table__deal-date">{listing.recentDealDate}</span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* === 모바일 카드 리스트 (768px 미만에서만 표시) === */}
      <div className="listings-table__cards">
        {sortedListings.map((listing) => (
          <article
            key={listing.id}
            className={`listing-card ${isBargain(listing) ? 'listing-card--bargain' : ''}`}
            onClick={() => handleRowClick(listing)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && handleRowClick(listing)}
            aria-label={`${listing.apartmentName} 매물 상세 보기`}
          >
            {/* 카드 상단: 아파트명 + 할인율 */}
            <div className="listing-card__header">
              <h3 className="listing-card__name">{listing.apartmentName}</h3>
              <span className={`listings-table__discount ${getDiscountClass(listing.discountRate)}`}>
                {formatDiscountRate(listing.discountRate)}
              </span>
            </div>

            {/* 카드 부가 정보: 동, 층, 면적 */}
            <div className="listing-card__sub">
              <span>{listing.dong || '-'}</span>
              <span className="listing-card__dot" aria-hidden="true" />
              <span>{formatFloor(listing.floor)}</span>
              <span className="listing-card__dot" aria-hidden="true" />
              <span>{formatArea(listing.areaSqm, listing.areaPyeong)}</span>
            </div>

            {/* 카드 가격 정보 그리드 */}
            <div className="listing-card__prices">
              <div className="listing-card__price-item">
                <span className="listing-card__price-label">호가</span>
                <span className="listing-card__price-value listing-card__price-value--asking">
                  {formatPrice(listing.askingPrice)}
                </span>
              </div>
              <div className="listing-card__price-item">
                <span className="listing-card__price-label">KB시세</span>
                <span className="listing-card__price-value">
                  {listing.kbPrice ? formatPrice(listing.kbPrice) : '-'}
                </span>
              </div>
              <div className="listing-card__price-item">
                <span className="listing-card__price-label">실거래가</span>
                <span className="listing-card__price-value">
                  {listing.recentDealPrice ? formatPrice(listing.recentDealPrice) : '-'}
                  {listing.recentDealDate && (
                    <span className="listing-card__deal-date"> ({listing.recentDealDate})</span>
                  )}
                </span>
              </div>
            </div>

            {/* 카드 하단: 등록일 */}
            <div className="listing-card__footer">
              <span className="listing-card__date">등록 {formatDate(listing.registeredAt)}</span>
              <span className="listing-card__link-hint">상세 보기</span>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
