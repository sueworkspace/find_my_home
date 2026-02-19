/**
 * Dashboard 컴포넌트
 *
 * 역할:
 * - 데이터 수집 현황 실시간 모니터링 대시보드
 * - DB 요약 통계 카드 (단지수, 매물수, KB시세, 급매 등)
 * - 스케줄러 상태 표시 (3개 잡 + 다음 실행 시각)
 * - 지역별 통계 테이블 (정렬 가능)
 * - 60초 자동 새로고침 + 수동 새로고침
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { getDashboardSummary, getSchedulerStatus, getRegionBreakdown, getAlertsBargains } from '../services/api';
import './Dashboard.css';

/** 자동 새로고침 간격 (ms) */
const AUTO_REFRESH_INTERVAL = 60_000;

/**
 * 숫자 포맷팅: 천 단위 콤마
 */
function formatNumber(n) {
  if (n == null) return '-';
  return n.toLocaleString('ko-KR');
}

/**
 * 날짜 포맷팅: YYYY-MM-DD HH:mm
 */
function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

/**
 * 만원 → 축약 가격 표기 (12.3억 / 9,500만)
 */
function formatPriceCompact(manwon) {
  if (manwon == null) return '-';
  if (manwon >= 10000) {
    const eok = manwon / 10000;
    return `${eok % 1 === 0 ? eok : eok.toFixed(1)}억`;
  }
  return `${manwon.toLocaleString()}만`;
}


/* ─── 통계 카드 ─── */
function DashboardStatCards({ summary }) {
  const cards = [
    { label: '전체 단지', value: summary.totalComplexes },
    { label: 'KB시세', value: summary.kbPricesCount },
    { label: '실거래', value: summary.realTransactionsCount },
    { label: '단지비교', value: summary.comparisonsCount },
    { label: '급매', value: summary.bargainsCount, accent: true },
  ];

  return (
    <div className="dashboard__cards">
      {cards.map((card) => (
        <div className="dashboard__card" key={card.label}>
          <div className={`dashboard__card-value ${card.accent ? 'dashboard__card-value--accent' : ''}`}>
            {formatNumber(card.value)}
          </div>
          <div className="dashboard__card-label">{card.label}</div>
        </div>
      ))}
      {/* 최근 업데이트 정보 */}
      {(summary.lastTransactionUpdate || summary.lastKbUpdate) && (
        <>
          <div className="dashboard__card">
            <div className="dashboard__card-sub">실거래 업데이트</div>
            <div className="dashboard__card-label">{formatDate(summary.lastTransactionUpdate)}</div>
          </div>
          <div className="dashboard__card">
            <div className="dashboard__card-sub">KB시세 업데이트</div>
            <div className="dashboard__card-label">{formatDate(summary.lastKbUpdate)}</div>
          </div>
        </>
      )}
    </div>
  );
}


/* ─── 스케줄러 상태 ─── */
function DashboardScheduler({ scheduler }) {
  return (
    <div>
      <div className="dashboard__scheduler-status">
        <span
          className={`dashboard__status-dot ${
            scheduler.isRunning ? 'dashboard__status-dot--running' : 'dashboard__status-dot--stopped'
          }`}
        />
        {scheduler.isRunning ? '스케줄러 실행 중' : '스케줄러 중지됨'}
      </div>

      {scheduler.jobs && scheduler.jobs.length > 0 && (
        <div className="dashboard__job-list">
          {scheduler.jobs.map((job) => (
            <div className="dashboard__job-item" key={job.jobId}>
              <span className="dashboard__job-name">{job.name}</span>
              <span className="dashboard__job-detail">
                트리거: {job.trigger}
              </span>
              <span className="dashboard__job-detail">
                다음 실행: {job.nextRunTime || '대기 중'}
                {job.isPaused && ' (일시정지)'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


/* ─── 지역 테이블 ─── */
function DashboardRegionTable({ regions }) {
  const [sortKey, setSortKey] = useState('sido');
  const [sortAsc, setSortAsc] = useState(true);

  /** 정렬 토글 핸들러 */
  const handleSort = (key) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  /** 정렬된 항목 */
  const sortedItems = [...(regions.items || [])].sort((a, b) => {
    const va = a[sortKey];
    const vb = b[sortKey];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;

    let cmp = 0;
    if (typeof va === 'string') {
      cmp = va.localeCompare(vb, 'ko');
    } else {
      cmp = va - vb;
    }
    return sortAsc ? cmp : -cmp;
  });

  /** 정렬 화살표 렌더링 */
  const renderArrow = (key) => {
    if (sortKey !== key) return null;
    return <span className="dashboard__sort-arrow">{sortAsc ? '\u25B2' : '\u25BC'}</span>;
  };

  const columns = [
    { key: 'sido', label: '시/도' },
    { key: 'sigungu', label: '시/군/구' },
    { key: 'complexCount', label: '단지' },
    { key: 'kbPriceCount', label: 'KB시세' },
    { key: 'dealCount', label: '실거래' },
    { key: 'comparisonCount', label: '비교' },
  ];

  return (
    <div className="dashboard__table-wrap">
      <table className="dashboard__table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} onClick={() => handleSort(col.key)}>
                {col.label}{renderArrow(col.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedItems.map((item, idx) => (
            <tr key={`${item.sido}-${item.sigungu}-${idx}`}>
              <td>{item.sido}</td>
              <td>{item.sigungu}</td>
              <td>{formatNumber(item.complexCount)}</td>
              <td>{formatNumber(item.kbPriceCount)}</td>
              <td>{formatNumber(item.dealCount)}</td>
              <td>{formatNumber(item.comparisonCount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


/**
 * BargainAlertPanel - 급매 알림 패널
 * 최근 N시간 내 등장한 급매 단지 목록을 표시합니다.
 */

/** sinceHours 버튼 옵션 */
const SINCE_HOURS_OPTIONS = [6, 12, 24, 48, 72];

function BargainAlertPanel() {
  const [minDiscount, setMinDiscount] = useState(5);
  const [sinceHours, setSinceHours] = useState(24);
  const [alerts, setAlerts] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /** 급매 알림 데이터 조회 */
  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAlertsBargains({ minDiscount, sinceHours, limit: 20 });
      setAlerts(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [minDiscount, sinceHours]);

  /* 조건 변경 시 자동 재조회 */
  useEffect(() => { fetchAlerts(); }, [fetchAlerts]);

  return (
    <div className="dashboard__alert-panel">
      {/* 조건 설정: 최소 할인율 슬라이더 + 기간 버튼 */}
      <div className="dashboard__alert-controls">
        <div className="dashboard__alert-slider-wrap">
          <label className="dashboard__alert-label">
            최소 할인율: <strong>{minDiscount}%</strong>
          </label>
          <input
            type="range"
            className="dashboard__alert-range"
            min="1"
            max="20"
            step="1"
            value={minDiscount}
            onChange={(e) => setMinDiscount(Number(e.target.value))}
            aria-label="최소 할인율 슬라이더"
          />
        </div>

        <div className="dashboard__alert-hours">
          {SINCE_HOURS_OPTIONS.map((h) => (
            <button
              key={h}
              className={`dashboard__alert-hour-btn ${sinceHours === h ? 'dashboard__alert-hour-btn--active' : ''}`}
              onClick={() => setSinceHours(h)}
            >
              {h}시간
            </button>
          ))}
        </div>
      </div>

      {/* 알림 목록 */}
      <div className="dashboard__alert-list">
        {loading && <div className="dashboard__alert-item--empty">불러오는 중...</div>}
        {error && <div className="dashboard__alert-item--empty dashboard__alert-item--error">{error}</div>}
        {!loading && !error && alerts && (
          <>
            {Array.isArray(alerts.items) && alerts.items.length > 0 ? (
              alerts.items.map((item, idx) => (
                <div className="dashboard__alert-item" key={`${item.complexId}-${item.areaSqm}-${idx}`}>
                  <div className="dashboard__alert-item-main">
                    <span className="dashboard__alert-item-name">{item.complexName}</span>
                    <span className={`dashboard__alert-item-rate ${item.discountRate > 0 ? 'dashboard__alert-item-rate--positive' : ''}`}>
                      {item.discountRate != null ? `${item.discountRate > 0 ? '+' : ''}${item.discountRate.toFixed(1)}%` : '-'}
                    </span>
                  </div>
                  <div className="dashboard__alert-item-sub">
                    <span>{item.sigungu}{item.dong ? ` ${item.dong}` : ''}</span>
                    <span>KB {formatPriceCompact(item.kbPrice)}</span>
                    <span>실거래 {formatPriceCompact(item.recentDealPrice)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="dashboard__alert-item--empty">
                조건에 맞는 급매가 없습니다.
              </div>
            )}
            {alerts.total != null && (
              <div className="dashboard__alert-total">총 {alerts.total}건</div>
            )}
          </>
        )}
      </div>
    </div>
  );
}


/* ─── 메인 대시보드 ─── */
export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [scheduler, setScheduler] = useState(null);
  const [regions, setRegions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [countdown, setCountdown] = useState(AUTO_REFRESH_INTERVAL / 1000);
  const timerRef = useRef(null);

  /** 데이터 로드 */
  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, schedulerData, regionsData] = await Promise.all([
        getDashboardSummary(),
        getSchedulerStatus(),
        getRegionBreakdown(),
      ]);
      setSummary(summaryData);
      setScheduler(schedulerData);
      setRegions(regionsData);
    } catch (err) {
      console.error('대시보드 데이터 로드 실패:', err);
      setError(err.message || '데이터를 불러오는 데 실패했습니다.');
    } finally {
      setLoading(false);
      setCountdown(AUTO_REFRESH_INTERVAL / 1000);
    }
  }, []);

  /** 초기 로드 + 60초 자동 새로고침 */
  useEffect(() => {
    fetchAll();

    const intervalId = setInterval(fetchAll, AUTO_REFRESH_INTERVAL);
    return () => clearInterval(intervalId);
  }, [fetchAll]);

  /** 카운트다운 타이머 */
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : AUTO_REFRESH_INTERVAL / 1000));
    }, 1000);

    return () => clearInterval(timerRef.current);
  }, []);

  /* 에러 표시 */
  if (error && !summary) {
    return <div className="dashboard__error">{error}</div>;
  }

  /* 초기 로딩 */
  if (loading && !summary) {
    return <div className="dashboard__loading">대시보드 데이터를 불러오는 중...</div>;
  }

  return (
    <div className="dashboard">
      {/* 급매 알림 */}
      <section className="dashboard__section">
        <div className="dashboard__section-header">
          <h2 className="dashboard__section-title">급매 알림</h2>
        </div>
        <BargainAlertPanel />
      </section>

      {/* DB 요약 통계 */}
      <section className="dashboard__section">
        <div className="dashboard__section-header">
          <h2 className="dashboard__section-title">DB 요약</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="dashboard__timer">{countdown}초 후 새로고침</span>
            <button
              className="dashboard__refresh-btn"
              onClick={fetchAll}
              disabled={loading}
            >
              <span className={`dashboard__refresh-icon ${loading ? 'dashboard__refresh-icon--spinning' : ''}`}>
                &#x21bb;
              </span>
              새로고침
            </button>
          </div>
        </div>
        {summary && <DashboardStatCards summary={summary} />}
      </section>

      {/* 스케줄러 상태 */}
      <section className="dashboard__section">
        <div className="dashboard__section-header">
          <h2 className="dashboard__section-title">스케줄러</h2>
        </div>
        {scheduler && <DashboardScheduler scheduler={scheduler} />}
      </section>

      {/* 지역별 통계 */}
      <section className="dashboard__section">
        <div className="dashboard__section-header">
          <h2 className="dashboard__section-title">
            지역별 현황 ({regions ? regions.totalRegions : 0}개 지역)
          </h2>
        </div>
        {regions && <DashboardRegionTable regions={regions} />}
      </section>
    </div>
  );
}
