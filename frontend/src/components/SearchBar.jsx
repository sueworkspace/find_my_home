/**
 * SearchBar 컴포넌트
 *
 * 역할:
 * - 단지명 검색 입력 필드
 * - 300ms 디바운스로 과도한 API 호출 방지
 * - 2글자 이상 입력 시 검색 실행, 빈 입력 시 초기화
 * - 클리어(X) 버튼으로 검색어 즉시 삭제
 * - Tailwind CSS 기반, CSS 파일 없음
 */
import { useState, useEffect, useRef } from 'react';

export default function SearchBar({ onSearch }) {
  const [inputValue, setInputValue] = useState('');
  const debounceRef = useRef(null);

  /* 입력값 변경 시 디바운스 적용 후 부모에 알림 */
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const trimmed = inputValue.trim();
      // 2글자 이상이면 검색, 빈 문자열이면 초기화
      if (trimmed.length >= 2 || trimmed.length === 0) {
        onSearch(trimmed);
      }
    }, 300);

    return () => clearTimeout(debounceRef.current);
  }, [inputValue, onSearch]);

  /* 클리어 버튼 클릭 */
  const handleClear = () => {
    setInputValue('');
    onSearch('');
  };

  return (
    <div className="w-full">
      {/* 검색 래퍼: 회색 배경 pill 형태 */}
      <div className="flex items-center gap-2 bg-[#F2F4F6] rounded-xl px-4 h-12">
        {/* 돋보기 아이콘 */}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-[#8B95A1] shrink-0"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>

        <input
          type="text"
          className="flex-1 bg-transparent text-[15px] text-[#191F28] placeholder:text-[#8B95A1] outline-none border-none"
          placeholder="아파트명 검색 (예: 래미안, 힐스테이트)"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          aria-label="단지명 검색"
        />

        {/* 클리어 버튼: 입력값이 있을 때만 표시 */}
        {inputValue && (
          <button
            type="button"
            onClick={handleClear}
            aria-label="검색어 지우기"
            className="flex items-center justify-center w-5 h-5 rounded-full bg-[#8B95A1] text-white text-[12px] leading-none shrink-0 hover:bg-[#4E5968] transition-colors"
          >
            ×
          </button>
        )}
      </div>

      {/* 안내 텍스트: 1글자만 입력한 경우 */}
      {inputValue.trim().length === 1 && (
        <p className="mt-1 px-1 text-[13px] text-[#8B95A1]">
          2글자 이상 입력하세요
        </p>
      )}
    </div>
  );
}
