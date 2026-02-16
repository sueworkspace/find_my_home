import { useState, useEffect } from 'react';
import { getSidoList, getSigunguList } from '../services/api';
import './RegionSelector.css';

export default function RegionSelector({ onRegionChange }) {
  const [sidoList, setSidoList] = useState([]);
  const [sigunguList, setSigunguList] = useState([]);
  const [selectedSido, setSelectedSido] = useState('');
  const [selectedSigungu, setSelectedSigungu] = useState('');
  const [loading, setLoading] = useState(false);

  // Load sido list on mount
  useEffect(() => {
    getSidoList().then(setSidoList);
  }, []);

  // Load sigungu list when sido changes
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

  // Notify parent when region selection is complete
  useEffect(() => {
    if (selectedSido && selectedSigungu) {
      onRegionChange(selectedSido, selectedSigungu);
    } else {
      onRegionChange(null, null);
    }
  }, [selectedSido, selectedSigungu]);

  const handleSidoChange = (e) => {
    setSelectedSido(e.target.value);
  };

  const handleSigunguChange = (e) => {
    setSelectedSigungu(e.target.value);
  };

  return (
    <div className="region-selector">
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
