/**
 * Header 컴포넌트
 *
 * 역할:
 * - 앱 상단에 고정(sticky) 표시되는 헤더
 * - 로고 아이콘 + 앱 이름 구성
 * - 탭 네비게이션: 단지 비교 ↔ 데이터 현황 전환
 * - Tailwind CSS 기반, CSS 파일 없음
 */
import { cn } from '@/lib/utils';

export default function Header({ activeView = 'listings', onViewChange }) {
  return (
    <header className="sticky top-0 z-50 bg-white border-b border-[#F2F4F6]">
      <div className="max-w-[1400px] mx-auto px-4">
        {/* 로고 + 탭을 한 줄에 */}
        <div className="flex items-center h-14 gap-6">

          {/* 로고 영역: 아이콘 + 타이틀 */}
          <div className="flex items-center gap-2 shrink-0">
            <svg
              width="26"
              height="26"
              viewBox="0 0 32 32"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              {/* 건물 실루엣 — Toss blue 계열 */}
              <path d="M16 2L2 9L16 16L30 9L16 2Z" fill="var(--color-brand)" />
              <path d="M2 9V23L16 30V16L2 9Z" fill="#4A90D9" />
              <path d="M30 9V23L16 30V16L30 9Z" fill="#2B74EA" />
              {/* 창문 — 흰색 */}
              <rect x="11" y="12" width="4" height="4" fill="#FFFFFF" opacity="0.9" />
              <rect x="17" y="12" width="4" height="4" fill="#FFFFFF" opacity="0.9" />
              <rect x="11" y="18" width="4" height="4" fill="#FFFFFF" opacity="0.6" />
              <rect x="17" y="18" width="4" height="4" fill="#FFFFFF" opacity="0.6" />
            </svg>
            <span className="text-[17px] font-bold text-[#191F28] tracking-tight">
              Find My Home
            </span>
          </div>

          {/* 탭 네비게이션 */}
          {onViewChange && (
            <nav className="flex items-end h-full gap-1" aria-label="주요 탭">
              {[
                { key: 'listings', label: '단지 비교' },
                { key: 'dashboard', label: '데이터 현황' },
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => onViewChange(key)}
                  className={cn(
                    'relative h-full px-3 text-[14px] font-medium transition-colors focus-visible:outline-none',
                    activeView === key
                      ? 'text-[var(--color-brand)] font-bold after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-[var(--color-brand)] after:rounded-t-sm'
                      : 'text-[#8B95A1] hover:text-[#4E5968]'
                  )}
                  aria-current={activeView === key ? 'page' : undefined}
                >
                  {label}
                </button>
              ))}
            </nav>
          )}
        </div>
      </div>
    </header>
  );
}
