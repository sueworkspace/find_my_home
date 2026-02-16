/**
 * API service layer - 실제 백엔드 연동
 */

const API_BASE_URL = '/api';

/**
 * snake_case → camelCase 변환
 */
function toCamelCase(str) {
  return str.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

function convertKeys(obj) {
  if (Array.isArray(obj)) return obj.map(convertKeys);
  if (obj !== null && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [toCamelCase(k), convertKeys(v)])
    );
  }
  return obj;
}

/**
 * Fetch list of 시/도
 */
export async function getSidoList() {
  const response = await fetch(`${API_BASE_URL}/regions/sido`);
  if (!response.ok) throw new Error('Failed to fetch sido list');
  const data = await response.json();
  return data.regions;
}

/**
 * Fetch list of 시/군/구 for a given 시/도
 */
export async function getSigunguList(sido) {
  const response = await fetch(`${API_BASE_URL}/regions/sigungu?sido=${encodeURIComponent(sido)}`);
  if (!response.ok) throw new Error('Failed to fetch sigungu list');
  const data = await response.json();
  return data.regions;
}

/**
 * Fetch listings for a given region
 */
export async function getListings(sido, sigungu) {
  const params = new URLSearchParams({ sido, sigungu, size: '100' });
  const response = await fetch(`${API_BASE_URL}/listings?${params}`);
  if (!response.ok) throw new Error('Failed to fetch listings');
  const data = await response.json();
  return convertKeys(data.items);
}
