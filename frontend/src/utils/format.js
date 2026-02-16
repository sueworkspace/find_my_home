/**
 * 포맷팅 유틸리티 (format.js)
 *
 * 역할:
 * - 매물 데이터의 가격, 면적, 할인율, 날짜, 층수를 사용자 친화적 문자열로 변환
 * - null/undefined 값은 '-'로 표시
 */

/**
 * 가격 포맷팅 (만원 → 억/만원 표기)
 * - 10000만원 이상: 억 단위로 변환 (예: 285000 → "28억 5,000만")
 * - 10000만원 미만: 만원 단위 표시 (예: 5000 → "5,000만")
 *
 * @param {number|null} price - 가격 (만원 단위)
 * @returns {string} 포맷된 가격 문자열
 */
export function formatPrice(price) {
  if (price == null) return '-';
  const eok = Math.floor(price / 10000);
  const man = price % 10000;
  if (eok > 0 && man > 0) {
    return `${eok}억 ${man.toLocaleString()}만`;
  } else if (eok > 0) {
    return `${eok}억`;
  } else {
    return `${man.toLocaleString()}만`;
  }
}

/**
 * 면적 포맷팅 (제곱미터 → 평형 + 제곱미터 병기)
 * - 예: "25평 (84.97m²)"
 *
 * @param {number|null} sqm - 면적 (제곱미터)
 * @param {number|null} pyeong - 면적 (평) - 없으면 sqm에서 자동 계산
 * @returns {string} 포맷된 면적 문자열
 */
export function formatArea(sqm, pyeong) {
  if (sqm == null) return '-';
  return `${pyeong || Math.round(sqm / 3.3058)}평 (${sqm}m\u00B2)`;
}

/**
 * 할인율 포맷팅
 * - 소수점 첫째 자리까지 표시 (예: "8.1%")
 *
 * @param {number|null} rate - 할인율 (백분율)
 * @returns {string} 포맷된 할인율 문자열
 */
export function formatDiscountRate(rate) {
  if (rate == null) return '-';
  return `${rate.toFixed(1)}%`;
}

/**
 * 날짜 포맷팅 (ISO/YYYY-MM-DD → MM.DD)
 * - 예: "2026-02-10" → "02.10"
 *
 * @param {string|null} dateStr - ISO 날짜 문자열 또는 YYYY-MM-DD
 * @returns {string} 포맷된 날짜 문자열
 */
export function formatDate(dateStr) {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${month}.${day}`;
}

/**
 * 층수 포맷팅
 * - 예: 15 → "15층"
 *
 * @param {number|null} floor - 층수
 * @returns {string} 포맷된 층수 문자열
 */
export function formatFloor(floor) {
  if (floor == null) return '-';
  return `${floor}층`;
}
