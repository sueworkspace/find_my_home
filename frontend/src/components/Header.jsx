/**
 * Header 컴포넌트
 *
 * 역할:
 * - 앱 상단에 고정(sticky) 표시되는 헤더
 * - 로고 아이콘 + 앱 이름 + 서비스 설명 구성
 * - 모바일에서는 세로 배치, 데스크톱에서는 가로 배치
 */
import './Header.css';

export default function Header() {
  return (
    <header className="header">
      <div className="header__inner">
        {/* 로고 영역: 아이콘 + 타이틀 */}
        <div className="header__logo">
          <svg
            className="header__icon"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path d="M16 2L2 9L16 16L30 9L16 2Z" fill="#FFFFFF" />
            <path d="M2 9V23L16 30V16L2 9Z" fill="rgba(255,255,255,0.7)" />
            <path d="M30 9V23L16 30V16L30 9Z" fill="rgba(255,255,255,0.5)" />
            <rect x="11" y="12" width="4" height="4" fill="#FFD700" opacity="0.9" />
            <rect x="17" y="12" width="4" height="4" fill="#FFD700" opacity="0.9" />
            <rect x="11" y="18" width="4" height="4" fill="#FFD700" opacity="0.7" />
            <rect x="17" y="18" width="4" height="4" fill="#FFD700" opacity="0.7" />
          </svg>
          <h1 className="header__title">Find My Home</h1>
        </div>

        {/* 서비스 설명 */}
        <p className="header__subtitle">KB시세 대비 급매물 탐지 서비스</p>
      </div>
    </header>
  );
}
