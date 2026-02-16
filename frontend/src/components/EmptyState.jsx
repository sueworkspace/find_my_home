/**
 * EmptyState 컴포넌트
 *
 * 역할:
 * - 다양한 빈 상태에 대한 사용자 친화적 안내 표시
 * - 상태 유형(type)에 따라 다른 아이콘/메시지 렌더링
 *
 * 지원하는 상태 유형:
 * - "no-region": 지역 미선택 상태
 * - "no-data": 선택한 지역에 매물 데이터 없음
 * - "no-results": 필터 조건에 맞는 매물 없음
 * - "error": API 호출 실패 등 에러 상태
 *
 * Props:
 * - type: 상태 유형 문자열
 * - message: (선택) 에러 타입에서 사용할 커스텀 메시지
 */
import './EmptyState.css';

export default function EmptyState({ type, message }) {
  /* 지역 미선택 상태 */
  if (type === 'no-region') {
    return (
      <div className="empty-state">
        <svg
          className="empty-state__icon"
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <circle cx="32" cy="32" r="28" stroke="#CBD5E1" strokeWidth="2" fill="#F1F5F9" />
          <path
            d="M32 18L20 26V44H28V36H36V44H44V26L32 18Z"
            fill="#94A3B8"
            stroke="#CBD5E1"
            strokeWidth="1.5"
          />
          <rect x="28" y="28" width="3" height="3" fill="#F1F5F9" />
          <rect x="33" y="28" width="3" height="3" fill="#F1F5F9" />
        </svg>
        <h3 className="empty-state__title">지역을 선택해주세요</h3>
        <p className="empty-state__desc">
          시/도와 시/군/구를 선택하면<br />
          해당 지역의 급매물 목록이 표시됩니다.
        </p>
      </div>
    );
  }

  /* 필터 결과 없음 상태 */
  if (type === 'no-results') {
    return (
      <div className="empty-state">
        <svg
          className="empty-state__icon"
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <circle cx="28" cy="28" r="16" stroke="#CBD5E1" strokeWidth="2" fill="#F1F5F9" />
          <line x1="39" y1="39" x2="52" y2="52" stroke="#CBD5E1" strokeWidth="3" strokeLinecap="round" />
          <line x1="22" y1="28" x2="34" y2="28" stroke="#94A3B8" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <h3 className="empty-state__title">조건에 맞는 매물이 없습니다</h3>
        <p className="empty-state__desc">
          필터 조건을 변경하거나<br />
          다른 지역을 선택해보세요.
        </p>
      </div>
    );
  }

  /* 매물 데이터 없음 상태 */
  if (type === 'no-data') {
    return (
      <div className="empty-state">
        <svg
          className="empty-state__icon"
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <rect x="12" y="8" width="40" height="48" rx="4" stroke="#CBD5E1" strokeWidth="2" fill="#F1F5F9" />
          <line x1="20" y1="20" x2="44" y2="20" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />
          <line x1="20" y1="28" x2="44" y2="28" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />
          <line x1="20" y1="36" x2="36" y2="36" stroke="#CBD5E1" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <h3 className="empty-state__title">매물 데이터가 없습니다</h3>
        <p className="empty-state__desc">
          선택한 지역에 등록된 매물이 없습니다.<br />
          다른 지역을 선택해보세요.
        </p>
      </div>
    );
  }

  /* 에러 상태: 사용자 친화적 에러 메시지 */
  if (type === 'error') {
    return (
      <div className="empty-state empty-state--error">
        <svg
          className="empty-state__icon"
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <circle cx="32" cy="32" r="28" stroke="#FCA5A5" strokeWidth="2" fill="#FEF2F2" />
          <path
            d="M32 20V36"
            stroke="#DC2626"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="32" cy="44" r="2" fill="#DC2626" />
        </svg>
        <h3 className="empty-state__title">오류가 발생했습니다</h3>
        <p className="empty-state__desc">
          {message || '매물 정보를 불러오는 데 실패했습니다.'}<br />
          잠시 후 다시 시도해주세요.
        </p>
      </div>
    );
  }

  return null;
}
