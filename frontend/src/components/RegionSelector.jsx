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
import './RegionSelector.css';

export default function RegionSelector({ onRegionChange }) {
  /* === 상태 === */
  const [sidoList, setSidoList] = useState([]);         // 시/도 목록
  const [sigunguList, setSigunguList] = useState([]);   // 시/군/구 목록
  const [selectedSido, setSelectedSido] = useState(''); // 선택된 시/도
  const [selectedSigungu, setSelectedSigungu] = useState(''); // 선택된 시/군/구
  const [loading, setLoading] = useState(false);        // 시/군/구 로딩 상태

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

  /** 시/도 셀렉트 변경 핸들러 */
  const handleSidoChange = (e) => {
    setSelectedSido(e.target.value);
  };

  /** 시/군/구 셀렉트 변경 핸들러 */
  const handleSigunguChange = (e) => {
    setSelectedSigungu(e.target.value);
  };

  return (
    <div className="region-selector">
      {/* 시/도 드롭다운 */}
      <div className="region-selector__group">
        <label className="region-selector__label" htmlFor="sido-select">
          시/도
        </label>
        <select
          id="sido-select"
          className="region-selector__select"
          value={selectedSido}
          onChange={handleSidoChange}
        >
          <option value="">시/도 선택</option>
          {sidoList.map((sido) => (
            <option key={sido} value={sido}>
              {sido}
            </option>
          ))}
        </select>
      </div>

      {/* 시/군/구 드롭다운 */}
      <div className="region-selector__group">
        <label className="region-selector__label" htmlFor="sigungu-select">
          시/군/구
        </label>
        <select
          id="sigungu-select"
          className="region-selector__select"
          value={selectedSigungu}
          onChange={handleSigunguChange}
          disabled={!selectedSido || loading}
        >
          <option value="">
            {loading ? '불러오는 중...' : '시/군/구 선택'}
          </option>
          {sigunguList.map((sigungu) => (
            <option key={sigungu} value={sigungu}>
              {sigungu}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
