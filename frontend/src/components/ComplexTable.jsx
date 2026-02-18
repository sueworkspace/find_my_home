/**
 * ComplexTable 컴포넌트
 *
 * KB시세 vs 실거래가 비교 단지 목록을 테이블로 렌더링합니다.
 * - 할인율 기준 색상 강조 (양수 = 급매 = 초록, 음수 = 빨강)
 * - 모바일: 카드 형태, 데스크톱: 테이블 형태
 */
import './ComplexTable.css';

/** 만원 → 억/만원 표기 변환 */
function formatPrice(manwon) {
  if (manwon == null) return '-';
  if (manwon >= 10000) {
    const eok = Math.floor(manwon / 10000);
    const rem = manwon % 10000;
    return rem > 0 ? `${eok}억 ${rem.toLocaleString()}만` : `${eok}억`;
  }
  return `${manwon.toLocaleString()}만`;
}

/** m² → 평형 변환 */
function sqmToPyeong(sqm) {
  return Math.round(sqm / 3.3058);
}

/** 할인율 표시 + 색상 클래스 */
function DiscountBadge({ rate }) {
  if (rate == null) return <span>-</span>;
  const isPositive = rate > 0;
  const cls = isPositive ? 'complex-table__badge--positive' : 'complex-table__badge--negative';
  const sign = isPositive ? '+' : '';
  return (
    <span className={`complex-table__badge ${cls}`}>
      {sign}{rate.toFixed(1)}%
    </span>
  );
}

export default function ComplexTable({ complexes }) {
  if (!complexes || complexes.length === 0) {
    return (
      <div className="complex-table__empty">
        비교 데이터가 없습니다. KB시세와 실거래가가 모두 수집된 단지만 표시됩니다.
      </div>
    );
  }

  return (
    <div className="complex-table__wrapper">
      <table className="complex-table">
        <thead>
          <tr>
            <th>아파트명</th>
            <th>지역</th>
            <th>면적</th>
            <th>KB시세</th>
            <th>실거래가</th>
            <th>할인율</th>
            <th>3개월 거래</th>
          </tr>
        </thead>
        <tbody>
          {complexes.map((item, idx) => (
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
              <td className="complex-table__price">{formatPrice(item.kbPriceMid)}</td>
              <td className="complex-table__price">{formatPrice(item.recentDealPrice)}</td>
              <td>
                <DiscountBadge rate={item.dealDiscountRate} />
              </td>
              <td className="complex-table__count">{item.dealCount3m}건</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
