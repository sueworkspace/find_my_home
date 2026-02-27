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

/** 자동 새로고침 간격 (ms) */
const AUTO_REFRESH_INTERVAL = 60_000;

/** 숫자 포맷팅: 천 단위 콤마 */
function formatNumber(n) {
  if (n == null) return '-';
  return n.toLocaleString('ko-KR');
}

/** 날짜 포맷팅: YYYY-MM-DD HH:mm */
function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '-';
  return d.toLocaleString('ko-KR', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

/** 만원 → 축약 가격 표기 (12.3억 / 9,500만) */
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
    <div className="grid grid-cols-2 gap-2 md:grid-cols-3 md:gap-3 lg:grid-cols-6">
      {cards.map((card) => (
        <div className="bg-[#F9FAFB] rounded-xl p-3 md:p-4 text-center" key={card.label}>
          <div className={`text-2xl md:text-[1.75rem] font-extrabold leading-tight ${card.accent ? 'text-[#F04251]' : 'text-[#1B64DA]'}`}>
            {formatNumber(card.value)}
          </div>
          <div className="text-[11px] md:text-xs text-[#8B95A1] mt-0.5">{card.label}</div>
        </div>
      ))}
      {/* 최근 업데이트 정보 */}
      {(summary.lastTransactionUpdate || summary.lastKbUpdate) && (
        <>
          <div className="bg-[#F9FAFB] rounded-xl p-3 md:p-4 text-center">
            <div className="text-[10px] text-[#D1D6DB] mt-0.5">실거래 업데이트</div>
            <div className="text-[11px] md:text-xs text-[#8B95A1] mt-0.5">{formatDate(summary.lastTransactionUpdate)}</div>
          </div>
          <div className="bg-[#F9FAFB] rounded-xl p-3 md:p-4 text-center">
            <div className="text-[10px] text-[#D1D6DB] mt-0.5">KB시세 업데이트</div>
            <div className="text-[11px] md:text-xs text-[#8B95A1] mt-0.5">{formatDate(summary.lastKbUpdate)}</div>
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
      <div className="flex items-center gap-2 mb-3 text-[13px] font-semibold">
        <span
          className={`w-2 h-2 rounded-full inline-block ${
            scheduler.isRunning
              ? 'bg-green-500 shadow-[0_0_4px_rgba(34,197,94,0.5)] animate-pulse'
              : 'bg-[#F04251]'
          }`}
        />
        {scheduler.isRunning ? '스케줄러 실행 중' : '스케줄러 중지됨'}
      </div>

      {scheduler.jobs && scheduler.jobs.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {scheduler.jobs.map((job) => (
            <div
              className="flex flex-col gap-0.5 px-3 py-2 bg-[#F9FAFB] rounded-lg text-xs md:flex-row md:items-center md:gap-4"
              key={job.jobId}
            >
              <span className="font-semibold text-[#191F28]">{job.name}</span>
              <span className="text-[#8B95A1]">트리거: {job.trigger}</span>
              <span className="text-[#8B95A1]">
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

  const columns = [
    { key: 'sido', label: '시/도' },
    { key: 'sigungu', label: '시/군/구' },
    { key: 'complexCount', label: '단지' },
    { key: 'kbPriceCount', label: 'KB시세' },
    { key: 'dealCount', label: '실거래' },
    { key: 'comparisonCount', label: '비교' },
  ];

  return (
    <div className="overflow-x-auto [-webkit-overflow-scrolling:touch]">
      <table className="w-full border-collapse text-xs whitespace-nowrap md:text-[13px]">
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className={`bg-[#F2F4F6] text-[#4E5968] font-semibold px-3 py-2 border-b-2 border-[#E5E8EB] cursor-pointer select-none sticky top-0 hover:bg-[#E5E8EB] transition-colors ${i >= 2 ? 'text-right' : 'text-left'}`}
              >
                {col.label}
                {sortKey === col.key && (
                  <span className="ml-1 text-[10px]">{sortAsc ? '\u25B2' : '\u25BC'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedItems.map((item, idx) => (
            <tr key={`${item.sido}-${item.sigungu}-${idx}`} className="hover:bg-[#F9FAFB] transition-colors">
              <td className="px-3 py-2 border-b border-[#F2F4F6] text-[#4E5968]">{item.sido}</td>
              <td className="px-3 py-2 border-b border-[#F2F4F6] text-[#4E5968]">{item.sigungu}</td>
              <td className="px-3 py-2 border-b border-[#F2F4F6] text-[#4E5968] text-right">{formatNumber(item.complexCount)}</td>
              <td className="px-3 py-2 border-b border-[#F2F4F6] text-[#4E5968] text-right">{formatNumber(item.kbPriceCount)}</td>
              <td className="px-3 py-2 border-b border-[#F2F4F6] text-[#4E5968] text-right">{formatNumber(item.dealCount)}</td>
              <td className="px-3 py-2 border-b border-[#F2F4F6] text-[#4E5968] text-right">{formatNumber(item.comparisonCount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


/** sinceHours 버튼 옵션 */
const SINCE_HOURS_OPTIONS = [6, 12, 24, 48, 72];

/* ─── 급매 알림 패널 ─── */
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
    <div className="bg-[#F9FAFB] border border-[#E5E8EB] rounded-xl p-4">
      {/* 조건 설정: 최소 할인율 슬라이더 + 기간 버튼 */}
      <div className="flex flex-col gap-3 mb-4 md:flex-row md:items-end">
        <div className="flex flex-col gap-1 md:flex-1">
          <label className="text-[13px] text-[#4E5968]">
            최소 할인율: <strong>{minDiscount}%</strong>
          </label>
          <input
            type="range"
            className="w-full accent-[#1B64DA]"
            min="1"
            max="20"
            step="1"
            value={minDiscount}
            onChange={(e) => setMinDiscount(Number(e.target.value))}
            aria-label="최소 할인율 슬라이더"
          />
        </div>

        <div className="flex gap-1.5 flex-wrap">
          {SINCE_HOURS_OPTIONS.map((h) => (
            <button
              key={h}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                sinceHours === h
                  ? 'bg-[#1B64DA] text-white border border-[#1B64DA]'
                  : 'bg-white text-[#4E5968] border border-[#E5E8EB] hover:bg-[#F2F4F6]'
              }`}
              onClick={() => setSinceHours(h)}
            >
              {h}시간
            </button>
          ))}
        </div>
      </div>

      {/* 알림 목록 */}
      <div className="flex flex-col gap-2">
        {loading && <div className="text-center py-4 text-[13px] text-[#8B95A1]">불러오는 중...</div>}
        {error && <div className="text-center py-4 text-[13px] text-[#F04251]">{error}</div>}
        {!loading && !error && alerts && (
          <>
            {Array.isArray(alerts.items) && alerts.items.length > 0 ? (
              alerts.items.map((item, idx) => (
                <div className="px-3 py-2.5 bg-white rounded-lg border border-[#E5E8EB]" key={`${item.complexId}-${item.areaSqm}-${idx}`}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-sm text-[#191F28]">{item.complexName}</span>
                    <span className={`font-semibold text-[13px] px-1.5 py-0.5 rounded ${
                      item.discountRate > 0
                        ? 'bg-[#FFF3F4] text-[#F04251]'
                        : 'bg-[#F2F4F6] text-[#8B95A1]'
                    }`}>
                      {item.discountRate != null ? `${item.discountRate > 0 ? '+' : ''}${item.discountRate.toFixed(1)}%` : '-'}
                    </span>
                  </div>
                  <div className="flex gap-3 text-xs text-[#8B95A1]">
                    <span>{item.sigungu}{item.dong ? ` ${item.dong}` : ''}</span>
                    <span>KB {formatPriceCompact(item.kbPrice)}</span>
                    <span>실거래 {formatPriceCompact(item.recentDealPrice)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-4 text-[13px] text-[#8B95A1]">
                조건에 맞는 급매가 없습니다.
              </div>
            )}
            {alerts.total != null && (
              <div className="text-right text-xs text-[#D1D6DB] pt-1">총 {alerts.total}건</div>
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
    return <div className="text-center py-10 text-sm text-[#F04251]">{error}</div>;
  }

  /* 초기 로딩 */
  if (loading && !summary) {
    return <div className="text-center py-10 text-sm text-[#8B95A1]">대시보드 데이터를 불러오는 중...</div>;
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 급매 알림 */}
      <section className="bg-white rounded-2xl shadow-sm p-4 lg:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-[#191F28]">급매 알림</h2>
        </div>
        <BargainAlertPanel />
      </section>

      {/* DB 요약 통계 */}
      <section className="bg-white rounded-2xl shadow-sm p-4 lg:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-[#191F28]">DB 요약</h2>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-[#D1D6DB]">{countdown}초 후 새로고침</span>
            <button
              className="inline-flex items-center gap-1 bg-[#1B64DA] text-white border-none rounded-lg px-3 py-1.5 text-xs font-semibold cursor-pointer transition-colors hover:bg-[#1554B8] disabled:opacity-60 disabled:cursor-not-allowed"
              onClick={fetchAll}
              disabled={loading}
            >
              <span className={`inline-block transition-transform ${loading ? 'animate-spin' : ''}`}>
                &#x21bb;
              </span>
              새로고침
            </button>
          </div>
        </div>
        {summary && <DashboardStatCards summary={summary} />}
      </section>

      {/* 스케줄러 상태 */}
      <section className="bg-white rounded-2xl shadow-sm p-4 lg:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-[#191F28]">스케줄러</h2>
        </div>
        {scheduler && <DashboardScheduler scheduler={scheduler} />}
      </section>

      {/* 지역별 통계 */}
      <section className="bg-white rounded-2xl shadow-sm p-4 lg:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-[#191F28]">
            지역별 현황 ({regions ? regions.totalRegions : 0}개 지역)
          </h2>
        </div>
        {regions && <DashboardRegionTable regions={regions} />}
      </section>
    </div>
  );
}
