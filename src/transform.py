"""
데이터 변환 및 정합성 체크 모듈
"""

import pandas as pd
import numpy as np
import re
import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# 컬럼명 매핑 (한글 -> 영문)
COLUMN_MAPPING = {
    '요일구분': 'day_type',
    '호선': 'line',
    '역번호': 'station_code',
    '출발역': 'station_name',
    '상하구분': 'direction'
}


def standardize_time_column(col_name: str) -> Optional[str]:
    """
    시간대 컬럼명을 표준 포맷으로 변환
    
    예: '5시30분' -> '05:30'
        '23시00분' -> '23:00'
    
    Parameters
    ----------
    col_name : str
        원본 컬럼명
    
    Returns
    -------
    str or None
        표준화된 시간 문자열 (HH:MM) 또는 None (시간 컬럼이 아닌 경우)
    """
    # 한글 시간 패턴 매칭: N시NN분
    pattern = r'(\d+)시(\d+)분'
    match = re.match(pattern, col_name)
    
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return f"{hour:02d}:{minute:02d}"
    
    return None


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    데이터프레임의 컬럼명을 표준화
    
    - 식별 컬럼: 한글 -> 영문 매핑
    - 시간대 컬럼: '5시30분' -> '05:30' 형식으로 변환
    
    Parameters
    ----------
    df : pd.DataFrame
        원본 데이터프레임
    
    Returns
    -------
    pd.DataFrame
        컬럼명이 표준화된 데이터프레임
    """
    df = df.copy()
    
    # 컬럼명 매핑 딕셔너리 생성
    rename_dict = {}
    
    for col in df.columns:
        # 식별 컬럼 매핑
        if col in COLUMN_MAPPING:
            rename_dict[col] = COLUMN_MAPPING[col]
        else:
            # 시간대 컬럼 표준화
            std_time = standardize_time_column(col)
            if std_time:
                rename_dict[col] = std_time
    
    df = df.rename(columns=rename_dict)
    
    logger.info(f"컬럼 표준화 완료: {len(rename_dict)}개 컬럼 변환")
    return df


def wide_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Wide 포맷을 Long 포맷으로 변환
    
    Parameters
    ----------
    df : pd.DataFrame
        Wide 포맷 데이터프레임 (시간대가 컬럼)
    
    Returns
    -------
    pd.DataFrame
        Long 포맷 데이터프레임 (time_slot, congestion 컬럼 추가)
    """
    # 식별 컬럼 (시간대가 아닌 컬럼들)
    id_cols = ['day_type', 'line', 'station_code', 'station_name', 'direction']
    
    # 실제로 존재하는 식별 컬럼만 사용
    id_cols = [col for col in id_cols if col in df.columns]
    
    # 시간대 컬럼 (나머지 모든 컬럼)
    time_cols = [col for col in df.columns if col not in id_cols]
    
    logger.info(f"Wide->Long 변환 시작: {len(time_cols)}개 시간대 컬럼")
    
    # Melt 수행
    df_long = df.melt(
        id_vars=id_cols,
        value_vars=time_cols,
        var_name='time_slot',
        value_name='congestion'
    )
    
    logger.info(f"변환 완료: {len(df)} 행 -> {len(df_long)} 행")
    
    return df_long


def clean_congestion_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    혼잡도 값 클렌징
    
    - 공백 제거
    - 문자열 -> float 변환
    - 음수/비정상 값 처리
    
    Parameters
    ----------
    df : pd.DataFrame
        congestion 컬럼을 포함한 데이터프레임
    
    Returns
    -------
    pd.DataFrame
        클렌징된 데이터프레임
    """
    df = df.copy()
    
    if 'congestion' not in df.columns:
        logger.warning("'congestion' 컬럼이 없습니다. 클렌징을 건너뜁니다.")
        return df
    
    # 문자열인 경우 공백 제거
    if df['congestion'].dtype == 'object':
        df['congestion'] = df['congestion'].astype(str).str.strip()
    
    # float 변환
    df['congestion'] = pd.to_numeric(df['congestion'], errors='coerce')
    
    # 음수 값 처리
    negative_count = (df['congestion'] < 0).sum()
    if negative_count > 0:
        logger.warning(f"음수 값 {negative_count}개 발견 -> NaN으로 처리")
        df.loc[df['congestion'] < 0, 'congestion'] = np.nan
    
    # 비정상적으로 높은 값 (200 초과)
    outlier_count = (df['congestion'] > 200).sum()
    if outlier_count > 0:
        logger.warning(f"200 초과 값 {outlier_count}개 발견 (최대: {df['congestion'].max():.1f})")
    
    return df


def clean_station_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    역명 표기 통일
    
    - 앞뒤 공백 제거
    - 특수문자 정리
    
    Parameters
    ----------
    df : pd.DataFrame
        station_name 컬럼을 포함한 데이터프레임
    
    Returns
    -------
    pd.DataFrame
        역명이 정리된 데이터프레임
    """
    df = df.copy()
    
    if 'station_name' not in df.columns:
        return df
    
    # 공백 제거
    df['station_name'] = df['station_name'].astype(str).str.strip()
    
    # 중복 공백 제거
    df['station_name'] = df['station_name'].str.replace(r'\s+', ' ', regex=True)
    
    return df


def validate_data(df: pd.DataFrame) -> Dict:
    """
    데이터 품질 검증 및 리포트 생성
    
    Parameters
    ----------
    df : pd.DataFrame
        검증할 데이터프레임
    
    Returns
    -------
    dict
        데이터 품질 리포트
    """
    report = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'columns': df.columns.tolist()
    }
    
    # 기본 통계
    if 'station_name' in df.columns:
        report['unique_stations'] = df['station_name'].nunique()
    
    if 'line' in df.columns:
        report['unique_lines'] = df['line'].nunique()
        report['lines'] = sorted(df['line'].unique().tolist())
    
    if 'time_slot' in df.columns:
        report['time_slots'] = df['time_slot'].nunique()
        report['time_slot_list'] = sorted(df['time_slot'].unique().tolist())
    
    if 'direction' in df.columns:
        report['direction_types'] = sorted(df['direction'].unique().tolist())
    
    if 'day_type' in df.columns:
        report['day_types'] = sorted(df['day_type'].unique().tolist())
    
    # 결측값
    null_counts = df.isnull().sum()
    report['null_count'] = {col: int(count) for col, count in null_counts.items() if count > 0}
    
    # 혼잡도 통계
    if 'congestion' in df.columns:
        congestion = df['congestion'].dropna()
        report['congestion_stats'] = {
            'count': len(congestion),
            'mean': float(congestion.mean()),
            'std': float(congestion.std()),
            'min': float(congestion.min()),
            'max': float(congestion.max()),
            'median': float(congestion.median())
        }
        
        # 0값 비율
        zero_count = (congestion == 0).sum()
        report['zero_ratio'] = float(zero_count / len(congestion))
        
        # 이상치
        report['outliers'] = {
            'negative': int((df['congestion'] < 0).sum()),
            'above_200': int((df['congestion'] > 200).sum())
        }
    
    logger.info("데이터 검증 완료")
    return report


def save_report(report: Dict, output_path: str):
    """
    데이터 품질 리포트를 JSON 파일로 저장
    
    Parameters
    ----------
    report : dict
        리포트 딕셔너리
    output_path : str
        저장할 파일 경로
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"리포트 저장 완료: {output_path}")


def run_pipeline(input_path: str, output_parquet: str, output_report: str) -> Tuple[pd.DataFrame, Dict]:
    """
    전체 데이터 변환 파이프라인 실행
    
    Parameters
    ----------
    input_path : str
        입력 CSV 파일 경로
    output_parquet : str
        출력 Parquet 파일 경로
    output_report : str
        품질 리포트 JSON 파일 경로
    
    Returns
    -------
    tuple
        (변환된 데이터프레임, 품질 리포트)
    """
    from .io import load_csv
    
    logger.info("=" * 60)
    logger.info("데이터 파이프라인 시작")
    logger.info("=" * 60)
    
    # 1. 로드
    logger.info(f"1단계: CSV 로드 - {input_path}")
    df = load_csv(input_path)
    logger.info(f"  로드 완료: {len(df)} 행, {len(df.columns)} 열")
    
    # 2. 컬럼 표준화
    logger.info("2단계: 컬럼 표준화")
    df = standardize_columns(df)
    
    # 3. Wide -> Long 변환
    logger.info("3단계: Wide -> Long 변환")
    df_long = wide_to_long(df)
    
    # 4. 데이터 클렌징
    logger.info("4단계: 데이터 클렌징")
    df_long = clean_congestion_values(df_long)
    df_long = clean_station_names(df_long)
    
    # 5. 정합성 체크
    logger.info("5단계: 데이터 검증")
    report = validate_data(df_long)
    
    # 6. 저장
    logger.info(f"6단계: 결과 저장")
    output_path = Path(output_parquet)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df_long.to_parquet(output_parquet, index=False)
    logger.info(f"  Parquet 저장 완료: {output_parquet}")
    
    save_report(report, output_report)
    
    logger.info("=" * 60)
    logger.info("파이프라인 완료")
    logger.info(f"  입력: {len(df)} 행 -> 출력: {len(df_long)} 행")
    logger.info(f"  파일 크기: {Path(output_parquet).stat().st_size / 1024:.1f} KB")
    logger.info("=" * 60)
    
    return df_long, report

