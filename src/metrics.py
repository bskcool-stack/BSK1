"""
집계 및 지표 계산 모듈 (Phase 2)

Streamlit 대시보드에서 빠르게 사용할 수 있도록
미리 집계된 테이블을 생성하고 캐시합니다.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# 혼잡도 등급 기준
CONGESTION_LEVELS = {
    "여유": (0, 30),
    "보통": (30, 60),
    "혼잡": (60, 90),
    "매우혼잡": (90, float("inf"))
}


def get_congestion_level(congestion: float) -> str:
    """
    혼잡도 값을 등급으로 변환
    
    Parameters
    ----------
    congestion : float
        혼잡도 값
    
    Returns
    -------
    str
        혼잡도 등급 (여유/보통/혼잡/매우혼잡)
    """
    for level, (min_val, max_val) in CONGESTION_LEVELS.items():
        if min_val <= congestion < max_val:
            return level
    return "매우혼잡"  # fallback


def calc_line_time_avg(df: pd.DataFrame) -> pd.DataFrame:
    """
    노선 × 시간대 평균 집계
    
    각 노선, 요일, 시간대별로 평균/최대/최소 혼잡도를 계산합니다.
    
    Parameters
    ----------
    df : pd.DataFrame
        congestion_long.parquet의 데이터프레임
    
    Returns
    -------
    pd.DataFrame
        노선 × 시간대 집계 테이블
    """
    logger.info("노선 × 시간대 평균 집계 시작")
    
    agg_df = df.groupby(['day_type', 'line', 'time_slot'], as_index=False).agg({
        'congestion': ['mean', 'max', 'min', 'std', 'count']
    })
    
    # 컬럼명 정리
    agg_df.columns = ['day_type', 'line', 'time_slot', 
                      'avg_congestion', 'max_congestion', 'min_congestion',
                      'std_congestion', 'sample_count']
    
    # 혼잡도 등급 추가
    agg_df['congestion_level'] = agg_df['avg_congestion'].apply(get_congestion_level)
    
    logger.info(f"노선 × 시간대 집계 완료: {len(agg_df)} 행")
    return agg_df


def calc_station_time_avg(df: pd.DataFrame) -> pd.DataFrame:
    """
    역 × 시간대 평균 집계
    
    각 역, 방향, 요일, 시간대별로 평균 혼잡도를 계산합니다.
    
    Parameters
    ----------
    df : pd.DataFrame
        congestion_long.parquet의 데이터프레임
    
    Returns
    -------
    pd.DataFrame
        역 × 시간대 집계 테이블
    """
    logger.info("역 × 시간대 평균 집계 시작")
    
    agg_df = df.groupby(['day_type', 'line', 'station_name', 'direction', 'time_slot'], 
                        as_index=False).agg({
        'congestion': ['mean', 'max', 'min']
    })
    
    # 컬럼명 정리
    agg_df.columns = ['day_type', 'line', 'station_name', 'direction', 'time_slot',
                      'avg_congestion', 'max_congestion', 'min_congestion']
    
    # 혼잡도 등급 추가
    agg_df['congestion_level'] = agg_df['avg_congestion'].apply(get_congestion_level)
    
    logger.info(f"역 × 시간대 집계 완료: {len(agg_df)} 행")
    return agg_df


def calc_top_n_congested(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    혼잡 TOP N 역 계산
    
    요일별로 평균 혼잡도가 가장 높은 N개의 역을 찾습니다.
    
    Parameters
    ----------
    df : pd.DataFrame
        congestion_long.parquet의 데이터프레임
    n : int, optional
        상위 N개 (기본값: 10)
    
    Returns
    -------
    pd.DataFrame
        혼잡 TOP N 역 테이블
    """
    logger.info(f"혼잡 TOP {n} 역 계산 시작")
    
    # 역별 평균 혼잡도 계산
    station_avg = df.groupby(['day_type', 'line', 'station_name', 'direction'], 
                             as_index=False).agg({
        'congestion': 'mean'
    }).rename(columns={'congestion': 'avg_congestion'})
    
    # 요일별 TOP N
    top_n_list = []
    for day_type in station_avg['day_type'].unique():
        day_df = station_avg[station_avg['day_type'] == day_type]
        top_n_day = day_df.nlargest(n, 'avg_congestion').copy()
        top_n_day['rank'] = range(1, len(top_n_day) + 1)
        top_n_day['rank_type'] = '혼잡'
        top_n_list.append(top_n_day)
    
    result = pd.concat(top_n_list, ignore_index=True)
    
    logger.info(f"혼잡 TOP {n} 완료: {len(result)} 행")
    return result


def calc_top_n_least_congested(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    여유 TOP N 역 계산
    
    요일별로 평균 혼잡도가 가장 낮은 N개의 역을 찾습니다.
    
    Parameters
    ----------
    df : pd.DataFrame
        congestion_long.parquet의 데이터프레임
    n : int, optional
        상위 N개 (기본값: 10)
    
    Returns
    -------
    pd.DataFrame
        여유 TOP N 역 테이블
    """
    logger.info(f"여유 TOP {n} 역 계산 시작")
    
    # 역별 평균 혼잡도 계산
    station_avg = df.groupby(['day_type', 'line', 'station_name', 'direction'], 
                             as_index=False).agg({
        'congestion': 'mean'
    }).rename(columns={'congestion': 'avg_congestion'})
    
    # 0값 제외 (운행하지 않는 시간대)
    station_avg = station_avg[station_avg['avg_congestion'] > 0]
    
    # 요일별 TOP N
    top_n_list = []
    for day_type in station_avg['day_type'].unique():
        day_df = station_avg[station_avg['day_type'] == day_type]
        top_n_day = day_df.nsmallest(n, 'avg_congestion').copy()
        top_n_day['rank'] = range(1, len(top_n_day) + 1)
        top_n_day['rank_type'] = '여유'
        top_n_list.append(top_n_day)
    
    result = pd.concat(top_n_list, ignore_index=True)
    
    logger.info(f"여유 TOP {n} 완료: {len(result)} 행")
    return result


def calc_peak_times(df: pd.DataFrame) -> pd.DataFrame:
    """
    각 역의 피크 시간대 및 최저 혼잡 시간대 계산
    
    역별로 혼잡도가 가장 높은/낮은 시간대를 찾습니다.
    
    Parameters
    ----------
    df : pd.DataFrame
        congestion_long.parquet의 데이터프레임
    
    Returns
    -------
    pd.DataFrame
        피크/최저 시간대 테이블
    """
    logger.info("피크 시간대 분석 시작")
    
    peak_list = []
    
    # 역별, 요일별, 방향별 그룹
    for (day_type, line, station, direction), group in df.groupby(
        ['day_type', 'line', 'station_name', 'direction']):
        
        # 0값 제외
        group_filtered = group[group['congestion'] > 0]
        
        if len(group_filtered) == 0:
            continue
        
        # 최대 혼잡도 시간대
        peak_row = group_filtered.loc[group_filtered['congestion'].idxmax()]
        
        # 최소 혼잡도 시간대
        least_row = group_filtered.loc[group_filtered['congestion'].idxmin()]
        
        peak_list.append({
            'day_type': day_type,
            'line': line,
            'station_name': station,
            'direction': direction,
            'peak_time': peak_row['time_slot'],
            'peak_congestion': peak_row['congestion'],
            'least_time': least_row['time_slot'],
            'least_congestion': least_row['congestion'],
            'avg_congestion': group['congestion'].mean(),
            'variance': group['congestion'].var()
        })
    
    result = pd.DataFrame(peak_list)
    
    logger.info(f"피크 시간대 분석 완료: {len(result)} 행")
    return result


def load_aggregated_data(base_path: str = "data/processed") -> Dict[str, pd.DataFrame]:
    """
    모든 집계 테이블 로드
    
    Parameters
    ----------
    base_path : str, optional
        집계 테이블이 저장된 디렉토리 경로
    
    Returns
    -------
    dict
        집계 테이블 딕셔너리
    """
    base_path = Path(base_path)
    
    data = {}
    
    files = {
        'line_time_avg': 'line_time_avg.parquet',
        'station_time_avg': 'station_time_avg.parquet',
        'top_congested': 'top_congested.parquet',
        'top_least_congested': 'top_least_congested.parquet',
        'peak_times': 'peak_times.parquet'
    }
    
    for key, filename in files.items():
        file_path = base_path / filename
        if file_path.exists():
            data[key] = pd.read_parquet(file_path)
            logger.info(f"로드 완료: {filename} ({len(data[key])} 행)")
        else:
            logger.warning(f"파일 없음: {filename}")
    
    return data


def run_aggregation_pipeline(
    input_path: str = "data/processed/congestion_long.parquet",
    output_dir: str = "data/processed"
) -> Dict[str, pd.DataFrame]:
    """
    전체 집계 파이프라인 실행
    
    Parameters
    ----------
    input_path : str
        입력 Parquet 파일 경로
    output_dir : str
        출력 디렉토리 경로
    
    Returns
    -------
    dict
        생성된 모든 집계 테이블
    """
    logger.info("=" * 60)
    logger.info("Phase 2: 집계 파이프라인 시작")
    logger.info("=" * 60)
    
    # 1. 원본 데이터 로드
    logger.info(f"1단계: 데이터 로드 - {input_path}")
    df = pd.read_parquet(input_path)
    logger.info(f"  로드 완료: {len(df)} 행, {len(df.columns)} 열")
    
    # 2. 집계 수행
    results = {}
    
    logger.info("2단계: 노선 × 시간대 평균 집계")
    results['line_time_avg'] = calc_line_time_avg(df)
    
    logger.info("3단계: 역 × 시간대 평균 집계")
    results['station_time_avg'] = calc_station_time_avg(df)
    
    logger.info("4단계: 혼잡 TOP 10 역 계산")
    results['top_congested'] = calc_top_n_congested(df, n=10)
    
    logger.info("5단계: 여유 TOP 10 역 계산")
    results['top_least_congested'] = calc_top_n_least_congested(df, n=10)
    
    logger.info("6단계: 피크 시간대 분석")
    results['peak_times'] = calc_peak_times(df)
    
    # 3. 저장
    logger.info("7단계: 결과 저장")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    file_mapping = {
        'line_time_avg': 'line_time_avg.parquet',
        'station_time_avg': 'station_time_avg.parquet',
        'top_congested': 'top_congested.parquet',
        'top_least_congested': 'top_least_congested.parquet',
        'peak_times': 'peak_times.parquet'
    }
    
    for key, filename in file_mapping.items():
        file_path = output_path / filename
        results[key].to_parquet(file_path, index=False)
        file_size = file_path.stat().st_size / 1024
        logger.info(f"  저장 완료: {filename} ({len(results[key])} 행, {file_size:.1f} KB)")
    
    logger.info("=" * 60)
    logger.info("Phase 2: 집계 파이프라인 완료")
    logger.info(f"  총 {len(results)} 개 집계 테이블 생성")
    logger.info("=" * 60)
    
    return results


# Streamlit 캐싱 함수 (Phase 3에서 사용)
def load_line_time_avg_cached(base_path: str = "data/processed") -> pd.DataFrame:
    """
    노선 × 시간대 평균 로드 (캐싱용)
    
    Streamlit에서 @st.cache_data 데코레이터와 함께 사용
    """
    return pd.read_parquet(Path(base_path) / "line_time_avg.parquet")


def load_station_time_avg_cached(base_path: str = "data/processed") -> pd.DataFrame:
    """
    역 × 시간대 평균 로드 (캐싱용)
    
    Streamlit에서 @st.cache_data 데코레이터와 함께 사용
    """
    return pd.read_parquet(Path(base_path) / "station_time_avg.parquet")

