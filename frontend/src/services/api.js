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
 * - min_discount 옵션으로 급매 필터링 가능 (서버사이드)
 *
 * @param {string} sido - 시/도 이름
 * @param {string} sigungu - 시/군/구 이름
 * @param {object} [options] - 추가 옵션
 * @param {number} [options.minDiscount] - 최소 할인율 (0 이상이면 급매만 조회)
 * @returns {Promise<Array>} 매물 객체 배열
 */
/* ─── 대시보드 API ─── */

/**
 * DB 요약 통계 조회
 * @returns {Promise<Object>} 단지수, 매물수, KB시세, 급매 등 통계
 */
export async function getDashboardSummary() {
  const response = await fetch(`${API_BASE_URL}/dashboard/summary`);
  if (!response.ok) throw new Error('대시보드 요약을 불러오는 데 실패했습니다.');
  return convertKeys(await response.json());
}

/**
 * 스케줄러 상태 조회
 * @returns {Promise<Object>} 스케줄러 실행 여부 및 잡 목록
 */
export async function getSchedulerStatus() {
  const response = await fetch(`${API_BASE_URL}/dashboard/scheduler`);
  if (!response.ok) throw new Error('스케줄러 상태를 불러오는 데 실패했습니다.');
  return convertKeys(await response.json());
}

/**
 * 지역별 통계 조회
 * @returns {Promise<Object>} 지역별 단지수, 매물수, KB시세, 급매 통계
 */
export async function getRegionBreakdown() {
  const response = await fetch(`${API_BASE_URL}/dashboard/regions`);
  if (!response.ok) throw new Error('지역별 통계를 불러오는 데 실패했습니다.');
  return convertKeys(await response.json());
}

/* ─── 단지 비교 API ─── */

/**
 * 단지 KB시세 vs 실거래가 비교 목록 조회
 * @param {object} [options] - 필터/정렬 옵션
 * @param {string} [options.sido] - 시/도 필터
 * @param {string} [options.sigungu] - 시/군/구 필터
 * @param {number} [options.minDiscount] - 최소 할인율 (급매 필터, 예: 0)
 * @param {string} [options.sortBy] - 정렬 기준 (deal_discount_rate 등)
 * @param {string} [options.order] - 정렬 방향 (desc | asc)
 * @param {number} [options.limit] - 최대 건수 (기본 100)
 * @returns {Promise<{total: number, items: Array}>}
 */
export async function getComplexes(options = {}) {
  const params = new URLSearchParams();
  if (options.sido) params.set('sido', options.sido);
  if (options.sigungu) params.set('sigungu', options.sigungu);
  if (options.minDiscount != null) params.set('min_discount', String(options.minDiscount));
  if (options.sortBy) params.set('sort_by', options.sortBy);
  if (options.order) params.set('order', options.order);
  if (options.limit) params.set('limit', String(options.limit));

  const response = await fetch(`${API_BASE_URL}/complexes?${params}`);
  if (!response.ok) throw new Error('단지 정보를 불러오는 데 실패했습니다.');
  const data = await response.json();
  return { total: data.total, items: convertKeys(data.items) };
}
