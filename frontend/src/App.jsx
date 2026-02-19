/**
 * App 컴포넌트 (최상위)
 *
 * 역할:
 * - 전체 앱 레이아웃 구성 (Header, RegionSelector, Filters, ComplexTable, Dashboard)
 * - 탭 전환: 단지 비교 ↔ 데이터 현황
 * - 지역 선택 → API 호출 → KB시세 vs 실거래가 비교 단지 목록 표시
 * - 클라이언트 사이드 필터링 (할인율, 가격, 면적, 급매)
 */
import { useState, useCallback, useMemo } from 'react';
import Header from './components/Header';
import RegionSelector from './components/RegionSelector';
import Filters from './components/Filters';
import ComplexTable from './components/ComplexTable';
import EmptyState from './components/EmptyState';
import LoadingSpinner from './components/LoadingSpinner';
import Dashboard from './components/Dashboard';
import { getComplexes } from './services/api';
import './App.css';

export default function App() {
  /* === 상태 관리 === */
  const [activeView, setActiveView] = useState('listings'); // 탭 전환 상태
  const [complexes, setComplexes] = useState([]);           // 단지 비교 목록
  const [total, setTotal] = useState(0);                    // 전체 건수
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [regionSelected, setRegionSelected] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState({ sido: null, sigungu: null });

  /* 통합 필터 상태 */
  const [filterState, setFilterState] = useState({
    minDiscount: 0,
    priceMin: 0, priceMax: Infinity, priceIndex: 0,
    areaMin: 0, areaMax: Infinity, areaIndex: 0,
    bargainOnly: false, minDiscountValue: 0,
  });

  /**
   * 지역 변경 핸들러
   * - 시/도, 시/군/구가 모두 선택되면 API 호출
   */
  const handleRegionChange = useCallback(async (sido, sigungu) => {
    setSelectedRegion({ sido, sigungu });
    setError(null);

    if (!sido || !sigungu) {
      setRegionSelected(false);
      setComplexes([]);
      setTotal(0);
      return;
    }

    setRegionSelected(true);
    setLoading(true);

    try {
      const result = await getComplexes({
        sido,
        sigungu,
        minDiscount: filterState.bargainOnly ? 0 : undefined,
        sortBy: 'deal_discount_rate',
        order: 'desc',
        limit: 500,
      });
      setComplexes(result.items);
      setTotal(result.total);
    } catch (err) {
      console.error('단지 조회 실패:', err);
      setError(err.message || '단지 정보를 불러오는 데 실패했습니다.');
      setComplexes([]);
    } finally {
      setLoading(false);
    }
  }, [filterState.bargainOnly]);

  /**
   * 필터 변경 핸들러
   * - bargainOnly 변경 시에만 서버 재조회
   * - 나머지 필터는 클라이언트 사이드 필터링
   */
  const handleFilterChange = useCallback(async (newFilters) => {
    const bargainChanged = newFilters.bargainOnly !== filterState.bargainOnly;
    setFilterState(newFilters);

    /* bargainOnly 토글이 변경된 경우에만 서버 재조회 */
    if (bargainChanged && selectedRegion.sido && selectedRegion.sigungu) {
      setLoading(true);
      setError(null);
      try {
        const result = await getComplexes({
          sido: selectedRegion.sido,
          sigungu: selectedRegion.sigungu,
          minDiscount: newFilters.bargainOnly ? 0 : undefined,
          sortBy: 'deal_discount_rate',
          order: 'desc',
          limit: 500,
        });
        setComplexes(result.items);
        setTotal(result.total);
      } catch (err) {
        setError(err.message || '단지 정보를 불러오는 데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    }
  }, [filterState.bargainOnly, selectedRegion]);

  /**
   * 클라이언트 사이드 필터링
   * - 할인율, 가격(KB시세), 면적(평형) 필터 적용
   */
  const filteredComplexes = useMemo(() => {
    return complexes.filter(item => {
      const pyeong = item.areaSqm / 3.3058;

      /* 급매만 보기: dealDiscountRate > minDiscountValue (최소 0 초과) */
      if (filterState.bargainOnly) {
        const minRate = filterState.minDiscountValue || 0;
        if (item.dealDiscountRate == null || item.dealDiscountRate <= minRate) return false;
      }

      /* 할인율 셀렉트 필터 */
      if (filterState.minDiscount > 0 && (item.dealDiscountRate == null || item.dealDiscountRate < filterState.minDiscount)) return false;

      /* 가격 필터 (KB시세 기준) */
      if (filterState.priceMin > 0 && item.kbPriceMid != null && item.kbPriceMid < filterState.priceMin) return false;
      if (filterState.priceMax !== Infinity && item.kbPriceMid != null && item.kbPriceMid > filterState.priceMax) return false;

      /* 면적 필터 (평형 기준) */
      if (pyeong < filterState.areaMin) return false;
      if (filterState.areaMax !== Infinity && pyeong > filterState.areaMax) return false;

      return true;
    });
  }, [complexes, filterState]);

  /** 상태에 따른 컨텐츠 렌더링 분기 */
  const renderContent = () => {
    if (!regionSelected) return <EmptyState type="no-region" />;
    if (loading) return <LoadingSpinner />;
    if (error) return <EmptyState type="error" message={error} />;
    if (filteredComplexes.length === 0) return <EmptyState type="no-data" />;
    return <ComplexTable complexes={filteredComplexes} />;
  };

  return (
    <div className="app">
      {/* 헤더: 앱 타이틀 + 탭 네비게이션 */}
      <Header activeView={activeView} onViewChange={setActiveView} />

      <main className="app__main">
        <div className="app__container">
          {/* 단지 비교 뷰 */}
          {activeView === 'listings' && (
            <>
              {/* 지역 선택기 */}
              <section className="app__section">
                <RegionSelector onRegionChange={handleRegionChange} />
              </section>

              {/* 선택된 지역 + 결과 건수 */}
              {regionSelected && (
                <div className="app__toolbar">
                  <span className="app__region-label">
                    {selectedRegion.sido} {selectedRegion.sigungu}
                    {!loading && (
                      <span className="app__count"> — {filteredComplexes.length}/{complexes.length}건</span>
                    )}
                  </span>
                </div>
              )}

              {/* 필터 패널: 지역 선택 후 표시 */}
              {regionSelected && (
                <Filters
                  filters={filterState}
                  onFilterChange={handleFilterChange}
                  totalCount={complexes.length}
                  filteredCount={filteredComplexes.length}
                />
              )}

              {/* 메인 컨텐츠 */}
              <section className="app__section app__section--content">
                {renderContent()}
              </section>
            </>
          )}

          {/* 데이터 현황 뷰 */}
          {activeView === 'dashboard' && (
            <section className="app__section">
              <Dashboard />
            </section>
          )}
        </div>
      </main>

      {/* 푸터 */}
      <footer className="app__footer">
        <p>
          Find My Home &middot; KB시세 vs 실거래가 비교 &middot;
          데이터는 참고용이며 투자 판단의 책임은 본인에게 있습니다.
        </p>
      </footer>
    </div>
  );
}
