# Phase 1 구현 완료 - 데이터 로딩/정리 파이프라인

## 개요
서울교통공사 지하철 혼잡도 데이터를 분석 가능한 형태로 변환하는 파이프라인을 구현했습니다.

## 구현 산출물

### 1. 코드 모듈
- **`src/io.py`**: CSV 로딩 및 인코딩 처리
  - 다중 인코딩 자동 감지 (cp949, euc-kr, utf-8)
  - 파일 정보 조회 기능
  
- **`src/transform.py`**: 데이터 변환 및 정합성 체크
  - 컬럼명 표준화 (한글→영문, 시간대 포맷 통일)
  - Wide→Long 포맷 변환
  - 데이터 클렌징 (공백 제거, 타입 변환, 이상치 처리)
  - 품질 검증 및 리포트 생성

- **`run_pipeline.py`**: 전체 파이프라인 실행 스크립트

### 2. 데이터 파일
- **`서울교통공사_지하철혼잡도정보_20250930.csv`**: 원본 데이터 (프로젝트 루트)
- **`data/processed/congestion_long.parquet`**: 변환된 Long 포맷 데이터 (123.9KB)
- **`data/processed/data_quality_report.json`**: 데이터 품질 리포트

## 데이터 변환 결과

### 변환 전 (Wide 포맷)
- 행: 1,671개
- 컬럼: 44개 (요일구분, 호선, 역번호, 출발역, 상하구분 + 시간대 39개)
- 형태: 각 시간대가 별도 컬럼

### 변환 후 (Long 포맷)
- 행: 65,169개
- 컬럼: 7개 (day_type, line, station_code, station_name, direction, time_slot, congestion)
- 형태: 시간대와 혼잡도가 행으로 변환

## 데이터 구조

| 컬럼명 | 설명 | 데이터 타입 | 예시 |
|--------|------|------------|------|
| day_type | 요일 구분 | string | 평일, 토요일, 일요일 |
| line | 노선명 | string | 1호선, 2호선, ... |
| station_code | 역 번호 | int | 150, 151, ... |
| station_name | 역명 | string | 서울역, 시청, ... |
| direction | 방향 | string | 상선, 하선, 내선, 외선 |
| time_slot | 시간대 | string | 05:30, 06:00, ... |
| congestion | 혼잡도 | float | 0.0 ~ 164.3 |

## 데이터 통계 요약

- **전체 행 수**: 65,169
- **고유 역 수**: 245개
- **노선 수**: 8개 (1~8호선)
- **시간대 수**: 39개 (05:30 ~ 00:30, 30분 단위)
- **방향 타입**: 상선, 하선, 내선, 외선
- **요일 타입**: 평일, 토요일, 일요일

### 혼잡도 통계
- 평균: 28.4
- 최소: 0.0
- 최대: 164.3
- 중앙값: 25.0
- 표준편차: 20.9

### 데이터 품질
- 결측값: 0개 (모든 필드 완전)
- 0값 비율: 5.7%
- 음수 값: 0개
- 200 초과 값: 0개

## 사용 방법

### 환경 설정
```bash
pip install -r requirements.txt
```

### 파이프라인 실행
```bash
python run_pipeline.py
```

### 변환된 데이터 사용
```python
import pandas as pd

# Parquet 파일 로드
df = pd.read_parquet('data/processed/congestion_long.parquet')

# 특정 역의 시간대별 혼잡도 조회
서울역_평일 = df[(df['station_name'] == '서울역') & 
                (df['day_type'] == '평일') & 
                (df['direction'] == '상선')]
print(서울역_평일[['time_slot', 'congestion']])
```

## 노선별 역 수

| 노선 | 역 수 |
|------|-------|
| 1호선 | 10개 |
| 2호선 | 52개 |
| 3호선 | 34개 |
| 4호선 | 26개 |
| 5호선 | 58개 |
| 6호선 | 40개 |
| 7호선 | 42개 |
| 8호선 | 19개 |

## 주요 기능

### 1. 인코딩 자동 감지
원본 CSV 파일이 cp949 인코딩으로 되어 있어도 자동으로 감지하여 로드합니다.

### 2. 컬럼명 표준화
- 한글 컬럼명을 영문으로 변환
- 시간대 컬럼 ('5시30분' → '05:30')을 표준 포맷으로 변환

### 3. 데이터 클렌징
- 혼잡도 값의 공백 제거
- 문자열을 float로 변환
- 음수/이상치 검증

### 4. 품질 리포트 자동 생성
변환 과정에서 데이터 품질 지표를 자동으로 계산하고 JSON 파일로 저장합니다.

## 다음 단계 (Phase 2)

Phase 1 완료 후 다음 단계는:
1. 집계/캐시 레이어 구현
2. 노선×시간대 평균
3. 역×시간대 평균
4. TOP N 혼잡/여유 역 계산
5. Streamlit 캐싱 전략 적용

## 파일 구조

```
BSK1/
├── src/
│   ├── __init__.py
│   ├── io.py              # CSV 로딩
│   └── transform.py       # 데이터 변환
├── data/
│   ├── raw/               # 원본 파일 보관 폴더
│   └── processed/
│       ├── congestion_long.parquet
│       └── data_quality_report.json
├── run_pipeline.py        # 실행 스크립트
├── requirements.txt
└── README_PHASE1.md       # 이 문서
```

## 기술 스택

- **Python 3.13**
- **pandas 2.0+**: 데이터 처리
- **pyarrow 12.0+**: Parquet 파일 입출력
- **numpy 1.24+**: 수치 연산

