/**
 * LoadingSpinner 컴포넌트
 *
 * 역할:
 * - 데이터 로딩 중 표시되는 스피너 애니메이션
 * - 로딩 메시지와 함께 사용자에게 대기 상태 안내
 * - 접근성: role="status"로 스크린리더에 로딩 상태 알림
 * - Tailwind animate-spin 사용, CSS 파일 없음
 */

export default function LoadingSpinner() {
  return (
    <div
      className="flex flex-col items-center justify-center py-20 gap-3"
      role="status"
      aria-label="로딩 중"
    >
      {/* SVG 링 스피너 — animate-spin */}
      <svg
        className="animate-spin text-[#1B64DA]"
        width="36"
        height="36"
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* 배경 트랙 */}
        <circle
          cx="18"
          cy="18"
          r="14"
          stroke="currentColor"
          strokeOpacity="0.15"
          strokeWidth="3"
        />
        {/* 회전 호 */}
        <path
          d="M18 4a14 14 0 0 1 14 14"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>

      <p className="text-[14px] text-[#8B95A1]">매물 정보를 불러오는 중...</p>
    </div>
  );
}
