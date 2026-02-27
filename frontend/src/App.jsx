/**
 * App 컴포넌트 (최상위)
 *
 * 역할:
 * - 전체 앱 레이아웃 구성 (Header, SearchBar, RegionSelector, Filters, ComplexTable, Dashboard)
 * - 탭 전환: 단지 비교 ↔ 데이터 현황
 * - 단지명 검색 또는 지역 선택 → API 호출 → KB시세 vs 실거래가 비교 단지 목록 표시
 * - 클라이언트 사이드 필터링 (할인율, 가격, 면적, 급매)
 * - Tailwind CSS 기반, App.css 제거
 */
import { useState, useCallback, useMemo, useRef } from 'react';
import Header from './components/Header';
import SearchBar from './components/SearchBar';
import RegionSelector from './components/RegionSelector';
import Filters from './components/Filters';
import ComplexTable from './components/ComplexTable';
import EmptyState from './components/EmptyState';
import LoadingSpinner from './components/LoadingSpinner';
import Dashboard from './components/Dashboard';
import { getComplexes } from './services/api';

export default function App() {
  /* === 상태 관리 === */
  const [activeView, setActiveView] = useState('listings'); // 탭 전환 상태
  const [complexes, setComplexes] = useState([]);           // 단지 비교 목록
  const [total, setTotal] = useState(0);                    // 전체 건수
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [regionSelected, setRegionSelected] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState({ sido: null, sigungu: null });
  const [searchText, setSearchText] = useState('');         // 단지명 검색어

  /* 최신 상태 참조 (콜백 내에서 stale closure 방지) */
  const searchTextRef = useRef('');
  const selectedRegionRef = useRef({ sido: null, sigungu: null });

  /* 통합 필터 상태 */
  const [filterState, setFilterState] = useState({
    minDiscount: 0,
    priceMin: 0, priceMax: Infinity, priceIndex: 0,
    areaMin: 0, areaMax: Infinity, areaIndex: 0,
    bargainOnly: false, minDiscountValue: 0,
    dateMonths: 0, dateIndex: 0,
  });
  const filterStateRef = useRef(filterState);

  /**
   * 공통 API 호출 헬퍼
   * - 검색어, 지역, 급매 필터를 조합하여 서버 조회
   */
  const fetchComplexes = useCallback(async ({ sido, sigungu, name, bargainOnly } = {}) => {
    const hasRegion = sido && sigungu;
    const hasName = name && name.length >= 2;

    /* 검색어도 없고 지역도 없으면 초기화 */
    if (!hasRegion && !hasName) {
      setComplexes([]);
      setTotal(0);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await getComplexes({
        sido: hasRegion ? sido : undefined,
        sigungu: hasRegion ? sigungu : undefined,
        name: hasName ? name : undefined,
        minDiscount: bargainOnly ? 0 : undefined,
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
  }, []);

  /**
   * 단지명 검색 핸들러 (SearchBar → App)
   * - 검색어 변경 시 서버 조회 (지역 선택과 조합 가능)
   */
  const handleSearch = useCallback((text) => {
    setSearchText(text);
    searchTextRef.current = text;
    const region = selectedRegionRef.current;
    fetchComplexes({
      sido: region.sido,
      sigungu: region.sigungu,
      name: text,
      bargainOnly: filterStateRef.current.bargainOnly,
    });
  }, [fetchComplexes]);

  /**
   * 지역 변경 핸들러
   * - 시/도, 시/군/구가 모두 선택되면 API 호출
   */
  const handleRegionChange = useCallback(async (sido, sigungu) => {
    setSelectedRegion({ sido, sigungu });
    selectedRegionRef.current = { sido, sigungu };
    setError(null);

    if (!sido || !sigungu) {
      setRegionSelected(false);
      /* 검색어가 없으면 초기화, 있으면 검색어로만 조회 */
      const curSearch = searchTextRef.current;
      if (!curSearch || curSearch.length < 2) {
        setComplexes([]);
        setTotal(0);
      }
      return;
    }

    setRegionSelected(true);
    fetchComplexes({
      sido,
      sigungu,
      name: searchTextRef.current,
      bargainOnly: filterStateRef.current.bargainOnly,
    });
  }, [fetchComplexes]);

  /**
   * 필터 변경 핸들러
   * - bargainOnly 변경 시에만 서버 재조회
   * - 나머지 필터는 클라이언트 사이드 필터링
   */
  const handleFilterChange = useCallback(async (newFilters) => {
    const bargainChanged = newFilters.bargainOnly !== filterStateRef.current.bargainOnly;
    setFilterState(newFilters);
    filterStateRef.current = newFilters;

    const region = selectedRegionRef.current;
    const hasRegion = region.sido && region.sigungu;
    const hasName = searchTextRef.current && searchTextRef.current.length >= 2;

    /* bargainOnly 토글이 변경된 경우에만 서버 재조회 */
    if (bargainChanged && (hasRegion || hasName)) {
      fetchComplexes({
        sido: region.sido,
        sigungu: region.sigungu,
        name: searchTextRef.current,
        bargainOnly: newFilters.bargainOnly,
      });
    }
  }, [fetchComplexes]);

  /**
   * 클라이언트 사이드 필터링
   * - 할인율, 가격(KB시세), 면적(평형) 필터 적용
   */
  const filteredComplexes = useMemo(() => {
    /* 거래일 필터: dateMonths > 0이면 해당 개월 이내만 통과 */
    let dateCutoff = null;
    if (filterState.dateMonths > 0) {
      dateCutoff = new Date();
      dateCutoff.setMonth(dateCutoff.getMonth() - filterState.dateMonths);
    }

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

      /* 거래일 필터 */
      if (dateCutoff) {
        if (!item.recentDealDate) return false;
        const dealDate = new Date(item.recentDealDate);
        if (dealDate < dateCutoff) return false;
      }

      return true;
    });
  }, [complexes, filterState]);

  /* 결과가 있는지 여부 (검색어 또는 지역 선택으로 데이터 로드됨) */
  const hasResults = regionSelected || (searchText && searchText.length >= 2);

  /** 상태에 따른 컨텐츠 렌더링 분기 */
  const renderContent = () => {
    if (!hasResults) return <EmptyState type="no-region" />;
    if (loading) return <LoadingSpinner />;
    if (error) return <EmptyState type="error" message={error} />;
    if (filteredComplexes.length === 0) return <EmptyState type="no-data" />;
    return <ComplexTable complexes={filteredComplexes} />;
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#F9FAFB]">
      {/* 헤더: 앱 타이틀 + 탭 네비게이션 */}
      <Header activeView={activeView} onViewChange={setActiveView} />

      <main className="flex-1 px-4 py-3">
        <div className="max-w-[1400px] mx-auto flex flex-col gap-3">

          {/* 단지 비교 뷰 */}
          {activeView === 'listings' && (
            <>
              {/* 단지명 검색 + 지역 선택 */}
              <section className="flex flex-col gap-2">
                <SearchBar onSearch={handleSearch} />
                <div>
                  <RegionSelector onRegionChange={handleRegionChange} />
                </div>
              </section>

              {/* 선택된 지역/검색어 + 필터 칩 행 */}
              {hasResults && (
                <div className="flex flex-col gap-2">
                  {/* 툴바: 지역 라벨 + 건수 */}
                  <div className="flex items-center px-1 pt-1">
                    <span className="text-[15px] font-bold text-[#191F28]">
                      {regionSelected
                        ? `${selectedRegion.sido} ${selectedRegion.sigungu}`
                        : '전국'}
                      {searchText && (
                        <span className="font-normal text-[#1B64DA]"> &middot; &ldquo;{searchText}&rdquo;</span>
                      )}
                      {!loading && (
                        <span className="font-normal text-[#8B95A1] text-[14px]"> — {filteredComplexes.length}/{complexes.length}건</span>
                      )}
                    </span>
                  </div>

                  {/* 필터 칩 */}
                  <Filters
                    filters={filterState}
                    onFilterChange={handleFilterChange}
                    totalCount={complexes.length}
                    filteredCount={filteredComplexes.length}
                  />
                </div>
              )}

              {/* 메인 컨텐츠 */}
              <section className="min-h-[300px] md:min-h-[400px]">
                {renderContent()}
              </section>
            </>
          )}

          {/* 데이터 현황 뷰 */}
          {activeView === 'dashboard' && (
            <section>
              <Dashboard />
            </section>
          )}
        </div>
      </main>

      {/* 푸터 */}
      <footer className="bg-[#191F28] text-[#8B95A1] text-center py-5 px-4 text-[12px] leading-relaxed mt-auto">
        <p>
          Find My Home &middot; KB시세 vs 실거래가 비교 &middot;
          데이터는 참고용이며 투자 판단의 책임은 본인에게 있습니다.
        </p>
      </footer>
    </div>
  );
}
