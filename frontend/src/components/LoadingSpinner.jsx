/**
 * LoadingSpinner 컴포넌트
 *
 * 역할:
 * - 데이터 로딩 중 표시되는 스피너 애니메이션
 * - 로딩 메시지와 함께 사용자에게 대기 상태 안내
 * - 접근성: role="status"로 스크린리더에 로딩 상태 알림
 */
import './LoadingSpinner.css';

export default function LoadingSpinner() {
  return (
    <div className="loading-spinner" role="status" aria-label="로딩 중">
      {/* 회전하는 링 애니메이션 (4개 div로 구성) */}
      <div className="loading-spinner__ring">
        <div></div>
        <div></div>
        <div></div>
        <div></div>
      </div>
      <p className="loading-spinner__text">매물 정보를 불러오는 중...</p>
      <p className="loading-spinner__subtext">잠시만 기다려주세요</p>
    </div>
  );
}
