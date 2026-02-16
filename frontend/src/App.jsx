/**
 * App 컴포넌트 (최상위)
 *
 * 역할:
 * - 전체 앱 레이아웃 구성 (Header, RegionSelector, Filters, ListingsTable)
 * - 지역 선택 → API 호출 → 매물 목록 관리
 * - 필터 상태 관리 및 매물 필터링 로직
 * - 로딩/에러/빈 상태에 따른 렌더링 분기
 */
import { useState, useCallback, useMemo } from 'react';
import Header from './components/Header';
import RegionSelector from './components/RegionSelector';
import Filters from './components/Filters';
import ListingsTable from './components/ListingsTable';
import EmptyState from './components/EmptyState';
import LoadingSpinner from './components/LoadingSpinner';
import { getListings } from './services/api';
import './App.css';

/** 필터 초기값 정의 */
const DEFAULT_FILTERS = {
  minDiscount: 0,
  priceMin: 0,
  priceMax: Infinity,
  priceIndex: 0,
  areaMin: 0,
  areaMax: Infinity,
  areaIndex: 0,
};

export default function App() {
  /* === 상태 관리 === */
  const [listings, setListings] = useState([]);        // 원본 매물 목록
  const [loading, setLoading] = useState(false);        // 로딩 상태
  const [error, setError] = useState(null);             // 에러 상태
  const [regionSelected, setRegionSelected] = useState(false); // 지역 선택 여부
  const [filters, setFilters] = useState(DEFAULT_FILTERS);     // 필터 상태
  const [selectedRegion, setSelectedRegion] = useState({ sido: null, sigungu: null });

  /**
   * 지역 변경 핸들러
   * - 시/도, 시/군/구가 모두 선택되면 API 호출
   * - 선택이 해제되면 매물 목록 초기화
   */
  const handleRegionChange = useCallback(async (sido, sigungu) => {
    setSelectedRegion({ sido, sigungu });
    setError(null);

    if (!sido || !sigungu) {
      setRegionSelected(false);
      setListings([]);
      setFilters(DEFAULT_FILTERS);
      return;
    }

    setRegionSelected(true);
    setLoading(true);
    setFilters(DEFAULT_FILTERS);

    try {
      const data = await getListings(sido, sigungu);
      setListings(data);
    } catch (err) {
      console.error('매물 조회 실패:', err);
      setError(err.message || '매물 정보를 불러오는 데 실패했습니다.');
      setListings([]);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 필터링된 매물 목록 (메모이제이션)
   * - 할인율, 호가, 면적 필터를 순차적으로 적용
   */
  const filteredListings = useMemo(() => {
    return listings.filter((listing) => {
      // 할인율 필터: 최소 할인율 이상만 통과
      if (filters.minDiscount > 0 && (listing.discountRate || 0) < filters.minDiscount) {
        return false;
      }

      // 호가 필터: 최소~최대 범위 내 매물만 통과
      if (listing.askingPrice < filters.priceMin || listing.askingPrice > filters.priceMax) {
        return false;
      }

      // 면적 필터: 평형 기준으로 범위 내 매물만 통과
      const pyeong = listing.areaPyeong || Math.round(listing.areaSqm / 3.3058);
      if (pyeong < filters.areaMin || pyeong > filters.areaMax) {
        return false;
      }

      return true;
    });
  }, [listings, filters]);

  /**
   * 상태에 따른 컨텐츠 렌더링 분기
   * - 지역 미선택 → 안내 메시지
   * - 로딩 중 → 스피너
   * - 에러 → 에러 메시지
   * - 데이터 없음 → 빈 상태 안내
   * - 필터 결과 없음 → 필터 조건 변경 안내
   * - 정상 → 매물 테이블
   */
  const renderContent = () => {
    if (!regionSelected) {
      return <EmptyState type="no-region" />;
    }

    if (loading) {
      return <LoadingSpinner />;
    }

    if (error) {
      return <EmptyState type="error" message={error} />;
    }

    if (listings.length === 0) {
      return <EmptyState type="no-data" />;
    }

    if (filteredListings.length === 0) {
      return <EmptyState type="no-results" />;
    }

    return <ListingsTable listings={filteredListings} />;
  };

  return (
    <div className="app">
      {/* 헤더: 앱 타이틀 및 설명 */}
      <Header />

      <main className="app__main">
        <div className="app__container">
          {/* 지역 선택기 */}
          <section className="app__section">
            <RegionSelector onRegionChange={handleRegionChange} />
          </section>

          {/* 선택된 지역 라벨 표시 */}
          {selectedRegion.sido && selectedRegion.sigungu && (
            <div className="app__region-label">
              {selectedRegion.sido} {selectedRegion.sigungu}
            </div>
          )}

          {/* 필터 패널: 매물이 있을 때만 표시 */}
          {regionSelected && listings.length > 0 && (
            <section className="app__section">
              <Filters
                filters={filters}
                onFilterChange={setFilters}
                totalCount={listings.length}
                filteredCount={filteredListings.length}
              />
            </section>
          )}

          {/* 메인 컨텐츠: 테이블 / 로딩 / 빈 상태 / 에러 */}
          <section className="app__section app__section--content">
            {renderContent()}
          </section>
        </div>
      </main>

      {/* 푸터 */}
      <footer className="app__footer">
        <p>
          Find My Home &middot; KB시세 대비 급매물 탐지 &middot; 데이터는 참고용이며 투자 판단의 책임은 본인에게 있습니다.
        </p>
      </footer>
    </div>
  );
}
