import { useState, useMemo } from 'react';
import { formatPrice, formatArea, formatDiscountRate, formatDate, formatFloor } from '../utils/format';
import './ListingsTable.css';

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

export default function ListingsTable({ listings }) {
  const [sortConfig, setSortConfig] = useState({ key: 'discountRate', direction: 'desc' });

  const sortedListings = useMemo(() => {
    if (!listings || listings.length === 0) return [];

    const sorted = [...listings].sort((a, b) => {
      const { key, direction } = sortConfig;
      let aVal = a[key];
      let bVal = b[key];

      // Handle null/undefined
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      // String comparison
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

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  };

  const getSortIndicator = (key) => {
    if (sortConfig.key !== key) return 'sort-indicator sort-indicator--inactive';
    return `sort-indicator sort-indicator--${sortConfig.direction}`;
  };

  const handleRowClick = (listing) => {
    if (listing.listingUrl) {
      window.open(listing.listingUrl, '_blank', 'noopener,noreferrer');
    }
  };

  if (!listings || listings.length === 0) {
    return null;
  }

  return (
    <div className="listings-table-wrapper">
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
              className="listings-table__row"
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
                <span
                  className={`listings-table__discount ${
                    listing.discountRate >= 7
                      ? 'listings-table__discount--high'
                      : listing.discountRate >= 5
                        ? 'listings-table__discount--mid'
                        : 'listings-table__discount--low'
                  }`}
                >
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
  );
}
