/**
 * EmptyState 컴포넌트
 *
 * 역할:
 * - 다양한 빈 상태에 대한 사용자 친화적 안내 표시
 * - 상태 유형(type)에 따라 다른 아이콘/메시지 렌더링
 * - Tailwind CSS 기반, CSS 파일 없음
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

export default function EmptyState({ type, message }) {
  /* 지역 미선택 상태 */
  if (type === 'no-region') {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <circle cx="32" cy="32" r="28" stroke="#D1D6DB" strokeWidth="2" fill="#F2F4F6" />
          <path
            d="M32 18L20 26V44H28V36H36V44H44V26L32 18Z"
            fill="#D1D6DB"
            stroke="#D1D6DB"
            strokeWidth="1.5"
          />
          <rect x="28" y="28" width="3" height="3" fill="#F2F4F6" />
          <rect x="33" y="28" width="3" height="3" fill="#F2F4F6" />
        </svg>
        <div>
          <h3 className="text-[15px] font-bold text-[#191F28] mb-1">지역을 선택해주세요</h3>
          <p className="text-[13px] text-[#8B95A1] leading-relaxed">
            시/도와 시/군/구를 선택하면<br />
            KB시세 대비 실거래가 비교 결과가 표시됩니다.
          </p>
        </div>
      </div>
    );
  }

  /* 필터 결과 없음 상태 */
  if (type === 'no-results') {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <circle cx="28" cy="28" r="16" stroke="#D1D6DB" strokeWidth="2" fill="#F2F4F6" />
          <line x1="39" y1="39" x2="52" y2="52" stroke="#D1D6DB" strokeWidth="3" strokeLinecap="round" />
          <line x1="22" y1="28" x2="34" y2="28" stroke="#8B95A1" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <div>
          <h3 className="text-[15px] font-bold text-[#191F28] mb-1">조건에 맞는 매물이 없습니다</h3>
          <p className="text-[13px] text-[#8B95A1] leading-relaxed">
            필터 조건을 변경하거나<br />
            다른 지역을 선택해보세요.
          </p>
        </div>
      </div>
    );
  }

  /* 비교 데이터 없음 상태 */
  if (type === 'no-data') {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <rect x="12" y="8" width="40" height="48" rx="4" stroke="#D1D6DB" strokeWidth="2" fill="#F2F4F6" />
          <line x1="20" y1="20" x2="44" y2="20" stroke="#D1D6DB" strokeWidth="2" strokeLinecap="round" />
          <line x1="20" y1="28" x2="44" y2="28" stroke="#D1D6DB" strokeWidth="2" strokeLinecap="round" />
          <line x1="20" y1="36" x2="36" y2="36" stroke="#D1D6DB" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <div>
          <h3 className="text-[15px] font-bold text-[#191F28] mb-1">비교 데이터가 없습니다</h3>
          <p className="text-[13px] text-[#8B95A1] leading-relaxed">
            KB시세와 실거래가가 모두 수집된 단지만 표시됩니다.<br />
            데이터 수집 후 조회해주세요.
          </p>
        </div>
      </div>
    );
  }

  /* 에러 상태 */
  if (type === 'error') {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
        <svg
          width="64"
          height="64"
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <circle cx="32" cy="32" r="28" stroke="#F04251" strokeWidth="2" fill="#FFF3F4" />
          <path
            d="M32 20V36"
            stroke="#F04251"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="32" cy="44" r="2" fill="#F04251" />
        </svg>
        <div>
          <h3 className="text-[15px] font-bold text-[#191F28] mb-1">오류가 발생했습니다</h3>
          <p className="text-[13px] text-[#8B95A1] leading-relaxed">
            {message || '매물 정보를 불러오는 데 실패했습니다.'}<br />
            잠시 후 다시 시도해주세요.
          </p>
        </div>
      </div>
    );
  }

  return null;
}
