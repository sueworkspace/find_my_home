# Find My Home - User Stories & MVP Feature Definition

## 1. Service Overview

**Find My Home**은 네이버 부동산에 등록된 급매물 중 KB시세(KB국민은행 부동산 시세)보다 저렴한 매물을 자동으로 탐지하고 사용자에게 알려주는 모니터링 서비스입니다.

### Background
- 다주택자 양도세 중과 유예 시한: **2026년 5월 9일**
- 시한 만료 전 다주택자들의 급매물 출현 증가 예상
- KB시세 대비 저렴한 매물을 빠르게 포착하는 것이 핵심 가치

### Target Users
- **Primary**: 아파트 매수를 희망하는 실수요자/투자자
- **Secondary**: 부동산 시장 동향을 모니터링하는 분석가

---

## 2. User Stories

### Epic 1: Data Collection (데이터 수집)

| ID | User Story | Priority | Sprint |
|----|-----------|----------|--------|
| US-101 | 사용자로서, 네이버 부동산의 아파트 매매 매물 정보를 자동으로 수집해주길 원한다. 그래야 일일이 검색하지 않아도 된다. | Must Have | Sprint 1 |
| US-102 | 사용자로서, KB시세 데이터를 자동으로 수집해주길 원한다. 그래야 시세 비교 기준이 정확하다. | Must Have | Sprint 1 |
| US-103 | 사용자로서, 내가 관심 있는 지역(시/구/동)을 설정할 수 있길 원한다. 그래야 관심 지역의 매물만 볼 수 있다. | Must Have | Sprint 1 |

**Acceptance Criteria (US-101):**
- [ ] 네이버 부동산 아파트 매매 매물 목록을 크롤링할 수 있다
- [ ] 매물 정보 포함: 단지명, 면적, 층수, 호가, 등록일, 매물 URL
- [ ] 주기적 자동 크롤링 (최소 1시간 간격)
- [ ] 크롤링 실패 시 에러 로깅 및 재시도

**Acceptance Criteria (US-102):**
- [ ] KB시세 데이터를 수집할 수 있다 (API 또는 크롤링)
- [ ] 시세 정보 포함: 단지명, 면적별 시세(하한/일반/상한)
- [ ] 시세 데이터 일 1회 이상 갱신

**Acceptance Criteria (US-103):**
- [ ] 시/도, 시/군/구, 읍/면/동 단위로 관심 지역을 설정할 수 있다
- [ ] 복수 지역 설정이 가능하다
- [ ] 설정한 지역의 매물만 크롤링 대상에 포함된다

---

### Epic 2: Price Comparison (가격 비교)

| ID | User Story | Priority | Sprint |
|----|-----------|----------|--------|
| US-201 | 사용자로서, 각 매물의 호가와 KB시세를 자동으로 비교해주길 원한다. 그래야 시세 대비 저렴한 매물을 빠르게 찾을 수 있다. | Must Have | Sprint 1 |
| US-202 | 사용자로서, KB시세 대비 할인율(%)을 한눈에 볼 수 있길 원한다. 그래야 얼마나 저렴한지 직관적으로 판단할 수 있다. | Must Have | Sprint 1 |
| US-203 | 사용자로서, 내가 원하는 할인율 기준(예: KB시세 대비 5% 이상 저렴)을 설정할 수 있길 원한다. 그래야 내 기준에 맞는 매물만 볼 수 있다. | Should Have | Sprint 2 |

**Acceptance Criteria (US-201):**
- [ ] 동일 단지, 동일 면적(전용면적 기준) 기준으로 매칭
- [ ] 매물 호가와 KB시세(일반가) 차액을 계산
- [ ] 매칭 실패 시 (KB시세 없음) 별도 표시

**Acceptance Criteria (US-202):**
- [ ] 할인율 = (KB시세 - 호가) / KB시세 * 100 으로 계산
- [ ] 할인율이 양수인 매물(시세보다 저렴)을 별도 표시
- [ ] 할인율 기준 정렬 가능

**Acceptance Criteria (US-203):**
- [ ] 사용자가 최소 할인율(%)을 설정할 수 있다 (예: 5%, 10%)
- [ ] 설정한 할인율 이상인 매물만 알림/대시보드에 표시된다
- [ ] 기본값은 0% (모든 시세 이하 매물 표시)

---

### Epic 3: 매물 리스트 웹페이지

| ID | User Story | Priority | Sprint |
|----|-----------|----------|--------|
| US-301 | 사용자로서, 시/도와 시/군/구를 선택하면 해당 지역의 아파트 매물 목록을 볼 수 있길 원한다. 그래야 관심 지역의 급매물을 한눈에 파악할 수 있다. | Must Have | Sprint 2 |
| US-302 | 사용자로서, 매물 리스트에서 아파트명, 동, 평형, 호가, KB시세, 할인율, 층수, 등록일, 최근 실거래가를 확인할 수 있길 원한다. 그래야 매물의 가치를 빠르게 판단할 수 있다. | Must Have | Sprint 2 |
| US-303 | 사용자로서, 매물을 할인율/가격/면적 기준으로 정렬하고 필터링할 수 있길 원한다. 그래야 원하는 조건의 매물을 쉽게 찾을 수 있다. | Must Have | Sprint 2 |
| US-304 | 사용자로서, 매물을 클릭하면 네이버 부동산 상세 페이지로 이동할 수 있길 원한다. 그래야 매물의 상세 정보를 확인할 수 있다. | Must Have | Sprint 2 |

**Acceptance Criteria (US-301):**
- [ ] 시/도 선택 드롭다운 제공
- [ ] 시/도 선택 시 해당 시/군/구 목록이 연동되어 표시
- [ ] 시/군/구 선택 시 해당 지역의 매물 리스트가 표시
- [ ] 반응형 웹 디자인 (모바일 지원)

**Acceptance Criteria (US-302):**
- [ ] 매물 리스트를 테이블 형태로 표시
- [ ] 표시 컬럼: 아파트명, 동, 평형(전용면적), 호가, KB시세, 할인율(%), 층수, 등록일, 최근 실거래가
- [ ] 할인율이 높은 매물(급매)은 시각적으로 강조 표시
- [ ] KB시세보다 저렴한 매물만 필터 가능

**Acceptance Criteria (US-303):**
- [ ] 할인율, 가격대, 면적(평형) 기준 필터링 가능
- [ ] 각 컬럼 기준 오름차순/내림차순 정렬 가능
- [ ] 필터 초기화 기능

**Acceptance Criteria (US-304):**
- [ ] 매물 행 클릭 시 네이버 부동산 매물 상세 페이지로 새 탭 이동

---

## 3. MVP Feature Definition

### MVP Scope (Sprint 1-2, 약 4주)

#### Must Have (P0) - Sprint 1
| Feature | Description | Stories |
|---------|-------------|---------|
| **네이버 부동산 크롤러** | 설정된 지역의 아파트 매매 매물을 주기적으로 수집 | US-101, US-103 |
| **KB시세 수집기** | KB시세 데이터를 수집하여 DB에 저장 | US-102 |
| **가격 비교 엔진** | 매물 호가와 KB시세를 자동 비교, 할인율 산출 | US-201, US-202 |

#### Must Have (P0) - Sprint 2
| Feature | Description | Stories |
|---------|-------------|---------|
| **지역 선택 매물 리스트** | 시/구 선택 시 해당 지역 매물 목록 표시 | US-301, US-302, US-304 |
| **필터/정렬** | 할인율, 가격, 면적 기준 필터링 및 정렬 | US-303 |

#### Should Have (P1) - Sprint 2
| Feature | Description | Stories |
|---------|-------------|---------|
| **할인율 기준 설정** | 사용자별 최소 할인율 기준 설정 | US-203 |

---

## 4. Sprint Plan

### Sprint 1 (Week 1-2): Data Foundation
**Goal**: 데이터 수집 파이프라인 구축 및 가격 비교 로직 완성

**Tasks:**
1. 프로젝트 초기 설정 (기술 스택, 프로젝트 구조, DB 스키마)
2. 네이버 부동산 크롤러 개발
   - API 분석 및 크롤링 로직 구현
   - 지역 설정 기능
   - 스케줄러 설정 (주기적 실행)
3. KB시세 데이터 수집기 개발
   - 데이터 소스 확보 (API/크롤링)
   - 시세 데이터 파싱 및 저장
4. 가격 비교 엔진 개발
   - 단지/면적 매칭 로직
   - 할인율 계산
5. 데이터 모델 및 DB 구축

**Definition of Done:**
- 지정 지역의 매물이 자동으로 수집된다
- KB시세 데이터가 수집/저장된다
- 매물별 KB시세 대비 할인율이 자동 산출된다

---

### Sprint 2 (Week 3-4): 매물 리스트 웹페이지
**Goal**: 사용자가 지역을 선택하여 급매물 리스트를 확인할 수 있는 웹페이지 구축

**Tasks:**
1. 지역 선택 UI 개발
   - 시/도, 시/군/구 드롭다운 연동
2. 매물 리스트 페이지 개발
   - 테이블: 아파트명, 동, 평형, 호가, KB시세, 할인율, 층수, 등록일, 최근 실거래가
   - 급매 강조 표시
   - 네이버 부동산 상세 링크
3. 필터/정렬 기능
   - 할인율, 가격대, 면적 필터
   - 컬럼별 정렬
4. 반응형 디자인 및 통합 테스트

**Definition of Done:**
- 시/구 선택 시 매물 리스트가 표시된다
- 할인율/가격/면적 기준 필터링 및 정렬이 동작한다
- 매물 클릭 시 네이버 부동산 상세 페이지로 이동한다

---

## 5. Technical Considerations

### 확정 Tech Stack
- **Frontend**: React
- **Backend**: Python (FastAPI)
- **Crawler**: Python (httpx + BeautifulSoup)
- **Database**: PostgreSQL
- **Scheduler**: APScheduler
- **Deployment**: Docker

### Key Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| 네이버 부동산 크롤링 차단 | 높음 | API 분석, rate limiting, user-agent rotation |
| KB시세 데이터 접근 제한 | 높음 | 공공 API 활용, 대안 데이터소스 확보 |
| 단지/면적 매칭 부정확 | 중간 | 단지 코드 기반 매칭, fuzzy matching |
| 양도세 중과 시한 연장 가능성 | 낮음 | 서비스 자체의 가치는 시한과 무관하게 유지 |

### Data Model (Core Entities)
```
Apartment Complex (아파트 단지)
- id, name, address, region_code, lat, lng

KB Price (KB 시세)
- id, complex_id, area_sqm, price_lower, price_mid, price_upper, updated_at

Listing (매물)
- id, complex_id, area_sqm, floor, asking_price, listing_url, source, created_at, is_active

Price Comparison (가격 비교)
- id, listing_id, kb_price_id, discount_rate, price_diff, compared_at

```

---

## 6. Success Metrics

| Metric | Target |
|--------|--------|
| 매물 수집 정확도 | > 95% |
| KB시세 매칭율 | > 90% |
| 페이지 로딩 시간 | < 3초 |
