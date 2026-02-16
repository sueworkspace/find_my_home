import { useState, useCallback, useMemo } from 'react';
import Header from './components/Header';
import RegionSelector from './components/RegionSelector';
import Filters from './components/Filters';
import ListingsTable from './components/ListingsTable';
import EmptyState from './components/EmptyState';
import LoadingSpinner from './components/LoadingSpinner';
import { getListings } from './services/api';
import './App.css';

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
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(false);
  const [regionSelected, setRegionSelected] = useState(false);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [selectedRegion, setSelectedRegion] = useState({ sido: null, sigungu: null });

  const handleRegionChange = useCallback(async (sido, sigungu) => {
    setSelectedRegion({ sido, sigungu });

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
    } catch (error) {
      console.error('Failed to fetch listings:', error);
      setListings([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const filteredListings = useMemo(() => {
    return listings.filter((listing) => {
      // Discount rate filter
      if (filters.minDiscount > 0 && (listing.discountRate || 0) < filters.minDiscount) {
        return false;
      }

      // Price filter (asking price in 만원)
      if (listing.askingPrice < filters.priceMin || listing.askingPrice > filters.priceMax) {
        return false;
      }

      // Area filter (in pyeong)
      const pyeong = listing.areaPyeong || Math.round(listing.areaSqm / 3.3058);
      if (pyeong < filters.areaMin || pyeong > filters.areaMax) {
        return false;
      }

      return true;
    });
  }, [listings, filters]);

  const renderContent = () => {
    if (!regionSelected) {
      return <EmptyState type="no-region" />;
    }

    if (loading) {
      return <LoadingSpinner />;
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
      <Header />

      <main className="app__main">
        <div className="app__container">
          {/* Region Selector */}
          <section className="app__section">
            <RegionSelector onRegionChange={handleRegionChange} />
          </section>

          {/* Selected region label */}
          {selectedRegion.sido && selectedRegion.sigungu && (
            <div className="app__region-label">
              {selectedRegion.sido} {selectedRegion.sigungu}
            </div>
          )}

          {/* Filters - only show when listings exist */}
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

          {/* Content: Table / Empty / Loading */}
          <section className="app__section app__section--content">
            {renderContent()}
          </section>
        </div>
      </main>

      <footer className="app__footer">
        <p>
          Find My Home &middot; KB시세 대비 급매물 탐지 &middot; 데이터는 참고용이며 투자 판단의 책임은 본인에게 있습니다.
        </p>
      </footer>
    </div>
  );
}
