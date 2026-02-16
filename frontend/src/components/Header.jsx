import './Header.css';

export default function Header() {
  return (
    <header className="header">
      <div className="header__inner">
        <div className="header__logo">
          <svg
            className="header__icon"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
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
        <p className="header__subtitle">KB시세 대비 급매물 탐지 서비스</p>
      </div>
    </header>
  );
}
