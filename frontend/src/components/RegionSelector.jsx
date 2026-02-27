/**
 * RegionSelector 컴포넌트
 *
 * 역할:
 * - 시/도 → 시/군/구 2단계 드롭다운 지역 선택기
 * - 시/도 선택 시 해당 시/군/구 목록을 API에서 자동 로드
 * - 두 드롭다운이 모두 선택되면 부모에 지역 변경 알림
 * - 모바일: 전체 너비 세로 배치, 데스크톱: 가로 배치
 */
import { useState, useEffect } from 'react';
import { getSidoList, getSigunguList } from '../services/api';

export default function RegionSelector({ onRegionChange }) {
  /* === 상태 === */
  const [sidoList, setSidoList] = useState([]);
  const [sigunguList, setSigunguList] = useState([]);
  const [selectedSido, setSelectedSido] = useState('');
  const [selectedSigungu, setSelectedSigungu] = useState('');
  const [loading, setLoading] = useState(false);

  /** 컴포넌트 마운트 시 시/도 목록 로드 */
  useEffect(() => {
    getSidoList().then(setSidoList);
  }, []);

  /** 시/도 변경 시 해당 시/군/구 목록 새로 로드 */
  useEffect(() => {
    if (!selectedSido) {
      setSigunguList([]);
      setSelectedSigungu('');
      return;
    }
    setLoading(true);
    setSelectedSigungu('');
    getSigunguList(selectedSido).then((list) => {
      setSigunguList(list);
      setLoading(false);
    });
  }, [selectedSido]);

  /** 시/도 + 시/군/구 선택 완료 시 부모 컴포넌트에 알림 */
  useEffect(() => {
    if (selectedSido && selectedSigungu) {
      onRegionChange(selectedSido, selectedSigungu);
    } else {
      onRegionChange(null, null);
    }
  }, [selectedSido, selectedSigungu]);

  /** 공통 셀렉트 스타일 */
  const selectClass =
    'w-full appearance-none rounded-xl border border-[#E5E8EB] bg-white px-3.5 py-2.5 text-[15px] text-[#191F28] ' +
    'bg-[url("data:image/svg+xml,%3Csvg%20xmlns=%27http://www.w3.org/2000/svg%27%20width=%2712%27%20height=%2712%27%20viewBox=%270%200%2012%2012%27%3E%3Cpath%20fill=%27%238B95A1%27%20d=%27M2.5%204.5L6%208l3.5-3.5%27/%3E%3C/svg%3E")] ' +
    'bg-no-repeat bg-[right_12px_center] bg-[length:12px] ' +
    'transition-colors duration-200 cursor-pointer ' +
    'hover:border-[#3182F6] focus:outline-none focus:border-[#3182F6] focus:ring-2 focus:ring-[#3182F6]/15 ' +
    'disabled:bg-[#F2F4F6] disabled:text-[#D1D6DB] disabled:cursor-not-allowed';

  return (
    <div className="flex flex-col gap-2 md:flex-row md:gap-3 md:items-end">
      {/* 시/도 드롭다운 */}
      <div className="flex flex-col gap-1 w-full md:w-auto md:min-w-[200px]">
        <label
          className="text-xs font-semibold text-[#8B95A1] tracking-wide"
          htmlFor="sido-select"
        >
          시/도
        </label>
        <select
          id="sido-select"
          className={selectClass}
          value={selectedSido}
          onChange={(e) => setSelectedSido(e.target.value)}
        >
          <option value="">시/도 선택</option>
          {sidoList.map((sido) => (
            <option key={sido} value={sido}>{sido}</option>
          ))}
        </select>
      </div>

      {/* 시/군/구 드롭다운 */}
      <div className="flex flex-col gap-1 w-full md:w-auto md:min-w-[200px]">
        <label
          className="text-xs font-semibold text-[#8B95A1] tracking-wide"
          htmlFor="sigungu-select"
        >
          시/군/구
        </label>
        <select
          id="sigungu-select"
          className={selectClass}
          value={selectedSigungu}
          onChange={(e) => setSelectedSigungu(e.target.value)}
          disabled={!selectedSido || loading}
        >
          <option value="">
            {loading ? '불러오는 중...' : '시/군/구 선택'}
          </option>
          {sigunguList.map((sigungu) => (
            <option key={sigungu} value={sigungu}>{sigungu}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
