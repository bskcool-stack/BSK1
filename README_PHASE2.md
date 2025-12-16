# Phase 2 구현 완료 - 집계/캐시 레이어

> **상태**: ✅ 완료  
> **완료일**: 2025-12-16  
> **작업자**: BSK1 Team

## 개요
Phase 1에서 생성된 정규화 데이터를 기반으로 Streamlit 대시보드에서 빠르게 사용할 수 있는 집계 테이블과 캐시 레이어를 구축했습니다.

## 구현 산출물

### 1. 코드 모듈 ✅
- ✅ **`src/metrics.py`**: 집계 및 지표 계산 모듈 (신규 생성)
  - 노선 × 시간대 평균 집계
  - 역 × 시간대 평균 집계
  - TOP N 혼잡/여유 역 계산
  - 피크 시간대 분석
  - Streamlit 캐싱 함수 (Phase 3 준비)

- ✅ **`run_pipeline.py`**: Phase 2 집계 단계 추가

### 2. 집계 데이터 파일 ✅

| 파일명 | 행 수 | 크기 | 설명 |
|--------|-------|------|------|
| `line_time_avg.parquet` | 936 | 26.6 KB | 노선 × 시간대 평균 |
| `station_time_avg.parquet` | 64,701 | 292.3 KB | 역 × 시간대 평균 |
| `top_congested.parquet` | 30 | 4.9 KB | 혼잡 TOP 10 역 |
| `top_least_congested.parquet` | 30 | 4.9 KB | 여유 TOP 10 역 |
| `peak_times.parquet` | 1,626 | 45.8 KB | 피크 시간대 분석 |

## 집계 테이블 상세

### 1. 노선 × 시간대 평균 (`line_time_avg.parquet`)

**컬럼 구조:**
- `day_type`: 요일 구분 (평일/토요일/일요일)
- `line`: 노선명 (1~8호선)
- `time_slot`: 시간대 (05:30 ~ 00:30)
- `avg_congestion`: 평균 혼잡도
- `max_congestion`: 최대 혼잡도
- `min_congestion`: 최소 혼잡도
- `std_congestion`: 표준편차
- `sample_count`: 샘플 수
- `congestion_level`: 혼잡도 등급 (여유/보통/혼잡/매우혼잡)

**행 수:** 936행 (8개 노선 × 39개 시간대 × 3개 요일)

### 2. 역 × 시간대 평균 (`station_time_avg.parquet`)

**컬럼 구조:**
- `day_type`: 요일 구분
- `line`: 노선명
- `station_name`: 역명
- `direction`: 방향 (상선/하선/내선/외선)
- `time_slot`: 시간대
- `avg_congestion`: 평균 혼잡도
- `max_congestion`: 최대 혼잡도
- `min_congestion`: 최소 혼잡도
- `congestion_level`: 혼잡도 등급

**행 수:** 64,701행

**용도:** 
- 특정 역의 시간대별 혼잡도 조회
- 상/하행(방향) 비교
- 시간대별 추이 시각화

### 3. 혼잡 TOP 10 역 (`top_congested.parquet`)

**컬럼 구조:**
- `day_type`: 요일 구분
- `line`: 노선명
- `station_name`: 역명
- `direction`: 방향
- `avg_congestion`: 평균 혼잡도
- `rank`: 순위 (1~10)
- `rank_type`: 랭킹 타입 ('혼잡')

**행 수:** 30행 (요일별 TOP 10 × 3개 요일)

**용도:** 대시보드 Overview 페이지에서 가장 혼잡한 역 표시

### 4. 여유 TOP 10 역 (`top_least_congested.parquet`)

**컬럼 구조:**
- `day_type`: 요일 구분
- `line`: 노선명
- `station_name`: 역명
- `direction`: 방향
- `avg_congestion`: 평균 혼잡도
- `rank`: 순위 (1~10)
- `rank_type`: 랭킹 타입 ('여유')

**행 수:** 30행 (요일별 TOP 10 × 3개 요일)

**용도:** 여유로운 역/시간대 추천

### 5. 피크 시간대 분석 (`peak_times.parquet`)

**컬럼 구조:**
- `day_type`: 요일 구분
- `line`: 노선명
- `station_name`: 역명
- `direction`: 방향
- `peak_time`: 최대 혼잡 시간대
- `peak_congestion`: 최대 혼잡도
- `least_time`: 최소 혼잡 시간대
- `least_congestion`: 최소 혼잡도
- `avg_congestion`: 평균 혼잡도
- `variance`: 분산

**행 수:** 1,626행

**용도:** 
- 역별 피크 시간대 확인
- 가장 덜 혼잡한 시간대 추천
- 혼잡도 변동성 분석

## 혼잡도 등급 기준

```python
CONGESTION_LEVELS = {
    "여유": (0, 30),      # 0 이상 30 미만
    "보통": (30, 60),     # 30 이상 60 미만
    "혼잡": (60, 90),     # 60 이상 90 미만
    "매우혼잡": (90, ∞)   # 90 이상
}
```

## 주요 함수

### 집계 함수

```python
# 노선 × 시간대 평균
calc_line_time_avg(df) -> pd.DataFrame

# 역 × 시간대 평균
calc_station_time_avg(df) -> pd.DataFrame

# 혼잡 TOP N 역
calc_top_n_congested(df, n=10) -> pd.DataFrame

# 여유 TOP N 역
calc_top_n_least_congested(df, n=10) -> pd.DataFrame

# 피크 시간대 분석
calc_peak_times(df) -> pd.DataFrame
```

### 유틸리티 함수

```python
# 모든 집계 테이블 로드
load_aggregated_data() -> dict

# 전체 집계 파이프라인 실행
run_aggregation_pipeline() -> dict

# 혼잡도 등급 변환
get_congestion_level(congestion: float) -> str
```

### Streamlit 캐싱 함수 (Phase 3 준비)

```python
# 노선 × 시간대 평균 로드 (캐싱용)
load_line_time_avg_cached() -> pd.DataFrame

# 역 × 시간대 평균 로드 (캐싱용)
load_station_time_avg_cached() -> pd.DataFrame
```

## 사용 방법

### 전체 파이프라인 실행

```bash
python run_pipeline.py
```

Phase 1 (데이터 변환) + Phase 2 (집계) 모두 실행됩니다.

### 집계 데이터만 재생성

```python
from src.metrics import run_aggregation_pipeline

# 집계 파이프라인만 실행
results = run_aggregation_pipeline(
    input_path="data/processed/congestion_long.parquet",
    output_dir="data/processed"
)
```

### 집계 테이블 로드

```python
from src.metrics import load_aggregated_data

# 모든 집계 테이블 로드
data = load_aggregated_data()

# 노선 × 시간대 평균
line_time_df = data['line_time_avg']

# 역 × 시간대 평균
station_time_df = data['station_time_avg']

# TOP 10 혼잡 역
top_congested_df = data['top_congested']
```

### 특정 집계 테이블만 로드

```python
import pandas as pd

# 노선 × 시간대 평균만 로드
line_time_df = pd.read_parquet('data/processed/line_time_avg.parquet')

# 평일 오전 8시 2호선 혼잡도
result = line_time_df[
    (line_time_df['day_type'] == '평일') &
    (line_time_df['line'] == '2호선') &
    (line_time_df['time_slot'] == '08:00')
]
print(result['avg_congestion'].values[0])
```

## 성능 최적화

### 1. Parquet 포맷 사용
- CSV 대비 빠른 읽기 속도
- 컬럼별 압축으로 파일 크기 감소
- 메타데이터 포함으로 스키마 보존

### 2. 미리 계산된 집계
- 대시보드에서 실시간 집계 불필요
- 필터링만으로 빠른 조회 가능

### 3. Streamlit 캐싱 준비
- `@st.cache_data` 데코레이터 사용 준비
- 파일 변경 시 자동 재로드

## 성능 지표

| 작업 | 소요 시간 |
|------|----------|
| Phase 1 (데이터 변환) | ~1초 |
| Phase 2 (집계) | ~2.5초 |
| 전체 파이프라인 | ~3.5초 |

**메모리 사용:**
- 원본 데이터 로드: ~10MB
- 집계 테이블 전체: ~370KB
- 실시간 메모리: < 50MB

## 작업 완료 체크리스트 ✅

- [x] `src/metrics.py` 모듈 생성
- [x] 노선 × 시간대 평균 집계 함수 구현
- [x] 역 × 시간대 평균 집계 함수 구현
- [x] TOP N 혼잡/여유 역 계산 함수 구현
- [x] 피크 시간대 분석 함수 구현
- [x] 혼잡도 등급 분류 함수 구현
- [x] 전체 집계 파이프라인 구현
- [x] `run_pipeline.py`에 Phase 2 단계 추가
- [x] 5개 집계 테이블 생성 및 검증
- [x] `requirements.txt`에 streamlit 추가
- [x] Phase 2 완료 문서 작성 ✨

## 다음 단계 (Phase 3)

Phase 2 완료 후 다음 단계는:
1. **Streamlit MVP UI 구현**
   - 페이지 1: Overview (요약)
   - 페이지 2: Station Detail (역 상세)
   - 페이지 3: Heatmap (히트맵)
2. **공통 필터 (사이드바)**
   - 노선 선택
   - 역 선택
   - 방향 선택
   - 요일 선택
   - 시간대 범위 선택
3. **캐싱 전략 적용**
   - `@st.cache_data` 데코레이터 활용
   - 집계 테이블 로드 캐싱
   - 필터 적용 결과 캐싱

## 파일 구조

```
BSK1/
├── src/
│   ├── __init__.py
│   ├── io.py                    # Phase 1: CSV 로딩
│   ├── transform.py             # Phase 1: 데이터 변환
│   └── metrics.py               # Phase 2: 집계/지표 계산 (신규)
├── data/
│   └── processed/
│       ├── congestion_long.parquet           # Phase 1 출력
│       ├── data_quality_report.json          # Phase 1 출력
│       ├── line_time_avg.parquet             # Phase 2 출력 (신규)
│       ├── station_time_avg.parquet          # Phase 2 출력 (신규)
│       ├── top_congested.parquet             # Phase 2 출력 (신규)
│       ├── top_least_congested.parquet       # Phase 2 출력 (신규)
│       └── peak_times.parquet                # Phase 2 출력 (신규)
├── run_pipeline.py              # Phase 1 + Phase 2 실행
├── requirements.txt             # streamlit 추가됨
├── README_PHASE1.md
└── README_PHASE2.md             # 이 문서
```

## 기술 스택

- **Python 3.13**
- **pandas 2.0+**: 데이터 처리 및 집계
- **pyarrow 12.0+**: Parquet 파일 입출력
- **numpy 1.24+**: 수치 연산
- **streamlit 1.28+**: 대시보드 구축 (Phase 3 준비)

## 참고 문서

- [Phase 1 완료 문서](README_PHASE1.md)
- [Streamlit 대시보드 계획](docs/streamlit-dashboard-plan.md)

