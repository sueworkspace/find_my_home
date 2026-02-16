/**
 * Utility functions for formatting values
 */

/**
 * Format price in 만원 to a readable string (억/만원)
 * @param {number} price - price in 만원
 * @returns {string}
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
 * Format area from sqm to pyeong display
 * @param {number} sqm
 * @param {number} pyeong
 * @returns {string}
 */
export function formatArea(sqm, pyeong) {
  if (sqm == null) return '-';
  return `${pyeong || Math.round(sqm / 3.3058)}평 (${sqm}m²)`;
}

/**
 * Format discount rate
 * @param {number} rate - discount rate as percentage
 * @returns {string}
 */
export function formatDiscountRate(rate) {
  if (rate == null) return '-';
  return `${rate.toFixed(1)}%`;
}

/**
 * Format date string
 * @param {string} dateStr - ISO date string or YYYY-MM-DD
 * @returns {string}
 */
export function formatDate(dateStr) {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${month}.${day}`;
}

/**
 * Format floor number
 * @param {number} floor
 * @returns {string}
 */
export function formatFloor(floor) {
  if (floor == null) return '-';
  return `${floor}층`;
}
