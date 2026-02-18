/**
 * App 컴포넌트 (최상위)
 *
 * 역할:
 * - 전체 앱 레이아웃 구성 (Header, RegionSelector, ComplexTable, Dashboard)
 * - 탭 전환: 단지 비교 ↔ 데이터 현황
 * - 지역 선택 → API 호출 → KB시세 vs 실거래가 비교 단지 목록 표시
 * - 급매 필터(할인율 > 0) 토글 지원
 */
import { useState, useCallback } from 'react';
import Header from './components/Header';
import RegionSelector from './components/RegionSelector';
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
  const [bargainOnly, setBargainOnly] = useState(false);    // 급매만 보기 필터

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
  }, [bargainOnly]);

  /**
   * 급매 필터 토글 핸들러
   * - 지역이 선택된 상태라면 즉시 재조회
   */
  const handleBargainToggle = useCallback(async () => {
    const newVal = !bargainOnly;
    setBargainOnly(newVal);

    if (!selectedRegion.sido || !selectedRegion.sigungu) return;

    setLoading(true);
    setError(null);
    try {
      const result = await getComplexes({
        sido: selectedRegion.sido,
        sigungu: selectedRegion.sigungu,
        minDiscount: newVal ? 0 : undefined,
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
  }, [bargainOnly, selectedRegion]);

  /** 상태에 따른 컨텐츠 렌더링 분기 */
  const renderContent = () => {
    if (!regionSelected) return <EmptyState type="no-region" />;
    if (loading) return <LoadingSpinner />;
    if (error) return <EmptyState type="error" message={error} />;
    if (complexes.length === 0) return <EmptyState type="no-data" />;
    return <ComplexTable complexes={complexes} />;
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

              {/* 선택된 지역 + 결과 건수 + 급매 필터 */}
              {regionSelected && (
                <div className="app__toolbar">
                  <span className="app__region-label">
                    {selectedRegion.sido} {selectedRegion.sigungu}
                    {!loading && (
                      <span className="app__count"> — {total}건</span>
                    )}
                  </span>

                  <button
                    className={`app__bargain-btn ${bargainOnly ? 'app__bargain-btn--active' : ''}`}
                    onClick={handleBargainToggle}
                  >
                    🏷 급매만 보기
                  </button>
                </div>
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
