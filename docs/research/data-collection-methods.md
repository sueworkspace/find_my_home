# 부동산 데이터 수집 방법 조사 보고서

> 프로젝트: 다주택자 양도세 중과 시한(2026.5.9) 전 아파트 급매물 모니터링 서비스
> 작성일: 2026-02-16

---

## 1. 네이버 부동산 (land.naver.com) 매물 데이터 크롤링

### 1.1 공식 API 여부

- 네이버는 부동산 매물 관련 **공식 API를 제공하지 않음**
- 프론트엔드가 호출하는 비공식 내부 API를 역분석하여 사용하는 방식
- 2024년 11월부터 독립 앱이 종료되고 네이버페이 앱에 통합됨 (API 구조 변경 가능성)

### 1.2 주요 API 엔드포인트 (비공식)

#### 매물 목록 조회
```
GET https://new.land.naver.com/api/articles/complex/{complexNo}
    ?realEstateType=APT
    &tradeType=A1
    &page=1
    &sameAddressGroup=true
```

#### 단지 정보 조회
```
GET https://fin.land.naver.com/front-api/v1/complex?complexNumber={complexNo}
```

#### 매물 상세 정보
```
GET https://fin.land.naver.com/front-api/v1/article/basicInfo
    ?articleId={articleId}
    &realEstateType=A02
    &tradeType=A1
```

#### 매물 키 정보 조회
```
GET https://fin.land.naver.com/front-api/v1/article/key?articleId={articleId}
```

#### 지역 목록
```
GET https://new.land.naver.com/api/regions/list
```

#### EV 충전 시설 등 부가정보
```
GET https://fin.land.naver.com/front-api/v1/complex/evStaion?complexNumber={complexNo}
```

### 1.3 주요 파라미터 코드

| 파라미터 | 값 | 설명 |
|---|---|---|
| realEstateType | APT | 아파트 |
| realEstateType | ABYG | 아파트분양권 |
| realEstateType | JGC | 재건축 |
| realEstateType | PRE | 분양권 |
| tradeType | A1 | 매매 |
| tradeType | B1 | 전세 |
| tradeType | B2 | 월세 |
| tradeType | B3 | 단기임대 |
| cortarNo | 1168010600 | 법정동코드 (예: 서울 강남구 대치동) |

### 1.4 필수 Request Headers

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
Referer: https://m.land.naver.com/
Host: new.land.naver.com
Sec-Fetch-Dest: empty
Sec-Fetch-Mode: cors
Sec-Fetch-Site: same-origin
Accept-Encoding: gzip
```

### 1.5 기술적 제약

- 짧은 시간 대량 요청시 **IP 차단** (일시적)
- 반복 요청시 **CAPTCHA** 발생 가능
- 요청 간 딜레이(1-2초 이상) 필요
- API 구조가 예고 없이 변경될 수 있음 (비공식이므로)

---

## 2. KB시세 데이터 접근 방법

### 2.1 방법 A: PublicDataReader 라이브러리 (권장)

**장점**: API 키 불필요, 가장 쉬운 접근법

```bash
pip install PublicDataReader
```

```python
from PublicDataReader import Kbland

api = Kbland()

# 사용 가능한 메서드
api.get_price_index()                    # 가격지수
api.get_price_index_change_rate()        # 가격지수 변화율
api.get_jeonse_price_ratio()             # 전세가격비율
api.get_jeonwolse_conversion_rate()      # 전월세 전환율
api.get_market_trend()                   # 시장 동향
api.get_price_index_by_area()            # 면적별 가격지수
api.get_average_price()                  # 평균가격
api.get_average_price_per_squaremeter()  # 평방미터당 평균가격
api.get_median_price()                   # 중간값 가격
```

**파라미터 예시**: 월간주간구분코드, 매물종별구분, 매매전세코드, 지역코드 등

### 2.2 방법 B: KB부동산 내부 API 직접 호출

```
GET https://data-api.kbland.kr/bfmstat/kbleadapt50/areaIndxAndAptPrcIndxAndRankgList
    ?topCd={topCode}
    &periodCd={periodCode}
    &lawdCd={lawdCode}
```

- 파라미터: TOP코드, 기간코드, 법정동코드 등
- 비공식 API이므로 변경 가능성 높음

### 2.3 방법 C: KB부동산 데이터허브 공식 서비스

- URL: https://data.kbland.kr
- 유료 데이터 서비스 포함
- 회원가입 후 데이터허브 이용 가이드 참조
- 가이드: https://file.kbland.kr/image/kbstar/land/pdf/datahub_guide_202307.pdf

---

## 3. 공공 데이터 API (가장 안정적이고 합법적)

### 3.1 국토교통부 실거래가 API (공공데이터포털)

#### 아파트 매매 실거래가

**엔드포인트 (신규):**
```
GET http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev
```

**엔드포인트 (구):**
```
GET http://openapi.molit.go.kr:8081/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTrade
```

#### 아파트 전월세 실거래가
- 공공데이터포털에서 별도 API 제공
- URL: https://www.data.go.kr/data/15126474/openapi.do

#### 필수 파라미터

| 파라미터 | 설명 | 예시 |
|---|---|---|
| serviceKey | API 인증키 | 공공데이터포털에서 발급 |
| LAWD_CD | 법정동코드 앞 5자리 | 11650 (서초구) |
| DEAL_YMD | 거래년월 6자리 | 202601 |

#### 응답 형식
- 기본: XML
- Python에서 `xmltodict` 라이브러리로 JSON 변환 가능

#### 사용 절차
1. https://data.go.kr 회원가입
2. "국토교통부_아파트 매매 실거래가 자료" API 활용 신청
3. 인증키 발급 (보통 1-2시간, 일부 24시간 소요)
4. API 호출

#### 요청 예시
```
http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev
  ?serviceKey={발급받은키}
  &LAWD_CD=11650
  &DEAL_YMD=202601
```

### 3.2 한국부동산원 R-ONE 통계 API

- URL: https://www.reb.or.kr/r-one
- 부동산 통계/지수 데이터 제공
- 인증키 발급 후 사용
- XML/JSON 출력 지원
- 연간 230만명 이상 이용하는 대표 부동산 통계 시스템
- 2025년 시스템 개편으로 Open API 및 기초 자료 확대

### 3.3 PublicDataReader 라이브러리 (통합 솔루션)

국토교통부 + KB부동산 데이터를 하나의 라이브러리로 조회 가능:
- GitHub: https://github.com/WooilJeong/PublicDataReader
- 공공데이터포털 API를 래핑한 Python 라이브러리
- 국토교통부 실거래가 + KB부동산 시세 통합 지원

```python
from PublicDataReader import TransactionPrice

# 공공데이터포털 API 키 필요
api = TransactionPrice(serviceKey="YOUR_SERVICE_KEY")

# 아파트 매매 실거래가 조회
df = api.get_data(
    property_type="아파트",
    trade_type="매매",
    sigungu_code="11650",
    year_month="202601"
)
```

---

## 4. 법적 크롤링 제한사항

### 4.1 최신 판례 (2024-2025)

#### 네이버 vs 다윈프로퍼티 (2024)
- **특허법원**: 다윈프로퍼티에 **8,000만원 배상** 명령
- 네이버 부동산 DB를 무단 복제/전송한 행위에 대해 **DB 저작권 침해** 인정
- 네이버는 확인매물 시스템에 약 10억원 투자, 데이터 편집/배열에 창작성 인정
- 1심(2024.9): 7,000만원 → 항소심(2024.12): 8,000만원으로 증액

#### 대법원 판례 (2022)
- 대법원 2022.5.12. 선고 2021도1533 판결
- 웹 크롤링을 통한 데이터 수집행위에 대한 형사법적 검토

### 4.2 이용약관 위반

- **네이버파이낸셜 서비스 이용약관 제10조**: 동의 없이 API에 접근하거나 크롤링 등 자동화된 수단을 통해 정보를 수집/이용하는 행위를 **명시적으로 금지**
- KB부동산도 유사한 이용약관 조항 존재 가능

### 4.3 robots.txt

- robots.txt 자체는 법적 구속력이 없음
- 그러나 크롤링 제한 의사 표시로 법원에서 해석될 수 있음
- 네이버는 2025년부터 AI 봇 크롤링도 차단 강화

### 4.4 법적 리스크 요약

| 데이터 소스 | 법적 리스크 | 비고 |
|---|---|---|
| 네이버 부동산 크롤링 | **높음** | 이용약관 위반 + DB 저작권 침해 판례 있음 |
| KB부동산 크롤링 | **높음** | 유사한 리스크 존재 |
| 공공데이터포털 API | **없음** | 공식 API 키 발급 후 합법 사용 |
| 한국부동산원 API | **없음** | 공식 API 키 발급 후 합법 사용 |
| PublicDataReader (KB 통계) | **낮음** | 공개된 통계 데이터 조회 |

---

## 5. 확정된 데이터 수집 전략

> **결정일: 2026-02-16** | 비상업적 개인 사용 목적

### 데이터 소스 확정

| 데이터 | 소스 | 용도 |
|---|---|---|
| **매물 호가** | 네이버 부동산 비공식 API | 현재 매물 가격 수집 (크롤링) |
| **KB시세** | KB부동산 데이터허브 (data.kbland.kr) | 시세 기준가 비교 |
| **실거래가** | 공공데이터포털 국토교통부 API | 실거래 이력 참조 |

### 1. 매물 호가: 네이버 부동산 크롤링

- 비공식 API 엔드포인트 활용 (섹션 1.2 참조)
- **비상업적 개인 사용 목적**으로 운영
- rate limiting 준수 (요청 간 1-2초 딜레이)
- IP 차단 대비 에러 핸들링 및 재시도 로직 구현

### 2. KB시세: KB부동산 데이터허브

- URL: https://data.kbland.kr
- 회원가입 후 데이터허브 이용
- 가이드: https://file.kbland.kr/image/kbstar/land/pdf/datahub_guide_202307.pdf
- 단지별/면적별 시세(하한/일반/상한) 확보

### 3. 실거래가: 공공데이터포털 API

- 국토교통부 아파트 매매 실거래가 API 사용
- 공공데이터포털 API 키 사전 발급 필요 (1-24시간 소요)
- 실거래 이력으로 시세 추이 분석 보조

### 급매물 판별 로직

1. 네이버 부동산에서 현재 매물 호가 수집
2. KB시세(데이터허브)에서 해당 단지/면적의 시세 조회
3. **할인율 = (KB시세 - 호가) / KB시세 × 100** 계산
4. 설정된 기준 이상 할인율 매물을 급매로 판별
5. 실거래가 데이터로 최근 거래 추이 참조

### 사전 준비 사항

- [ ] 공공데이터포털 API 키 발급 (https://data.go.kr)
- [ ] KB부동산 데이터허브 회원가입 (https://data.kbland.kr)

---

## 참고 자료

- [PublicDataReader GitHub](https://github.com/WooilJeong/PublicDataReader)
- [공공데이터포털 - 아파트 매매 실거래가](https://www.data.go.kr/data/15126469/openapi.do)
- [공공데이터포털 - 아파트 전월세 실거래가](https://www.data.go.kr/data/15126474/openapi.do)
- [KB부동산 데이터허브](https://data.kbland.kr/)
- [국토교통부 실거래가공개시스템](https://rt.molit.go.kr/)
