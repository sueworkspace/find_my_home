/**
 * API 서비스 레이어 (api.js)
 *
 * 역할:
 * - 백엔드 API와의 통신을 담당하는 서비스 모듈
 * - snake_case → camelCase 키 변환 유틸리티 포함
 * - 시/도 목록, 시/군/구 목록, 매물 목록 조회 API 제공
 */

/** API 기본 URL (Vite 프록시를 통해 백엔드로 전달) */
const API_BASE_URL = '/api';

/**
 * snake_case 문자열을 camelCase로 변환
 * 예: "asking_price" → "askingPrice"
 */
function toCamelCase(str) {
  return str.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

/**
 * 객체/배열의 모든 키를 재귀적으로 camelCase로 변환
 * - 백엔드 응답(snake_case)을 프론트엔드 규칙(camelCase)에 맞게 변환
 */
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
 * 시/도 목록 조회 API
 * @returns {Promise<string[]>} 시/도 이름 배열
 */
export async function getSidoList() {
  const response = await fetch(`${API_BASE_URL}/regions/sido`);
  if (!response.ok) throw new Error('시/도 목록을 불러오는 데 실패했습니다.');
  const data = await response.json();
  return data.regions;
}

/**
 * 시/군/구 목록 조회 API
 * @param {string} sido - 선택된 시/도 이름
 * @returns {Promise<string[]>} 시/군/구 이름 배열
 */
export async function getSigunguList(sido) {
  const response = await fetch(`${API_BASE_URL}/regions/sigungu?sido=${encodeURIComponent(sido)}`);
  if (!response.ok) throw new Error('시/군/구 목록을 불러오는 데 실패했습니다.');
  const data = await response.json();
  return data.regions;
}

/**
 * 매물 목록 조회 API
 * - 선택된 지역의 매물 최대 100건 조회
 * - 응답 데이터의 키를 camelCase로 변환하여 반환
 *
 * @param {string} sido - 시/도 이름
 * @param {string} sigungu - 시/군/구 이름
 * @returns {Promise<Array>} 매물 객체 배열
 */
export async function getListings(sido, sigungu) {
  const params = new URLSearchParams({ sido, sigungu, size: '100' });
  const response = await fetch(`${API_BASE_URL}/listings?${params}`);
  if (!response.ok) throw new Error('매물 정보를 불러오는 데 실패했습니다.');
  const data = await response.json();
  return convertKeys(data.items);
}
