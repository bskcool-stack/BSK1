"""
서울교통공사 지하철 혼잡도 대시보드 - 메인 진입점

Phase 3: Streamlit MVP UI
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.metrics import get_congestion_level

# 페이지 설정
st.set_page_config(
    page_title="지하철 혼잡도 대시보드",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 혼잡도 등급별 색상 매핑
CONGESTION_COLORS = {
    "여유": "#28a745",      # 녹색
    "보통": "#ffc107",      # 노랑
    "혼잡": "#fd7e14",      # 주황
    "매우혼잡": "#dc3545"   # 빨강
}


@st.cache_data
def load_line_time_avg():
    """노선 × 시간대 평균 데이터 로드 (캐싱)"""
    return pd.read_parquet("data/processed/line_time_avg.parquet")


@st.cache_data
def load_station_time_avg():
    """역 × 시간대 평균 데이터 로드 (캐싱)"""
    return pd.read_parquet("data/processed/station_time_avg.parquet")


@st.cache_data
def load_top_congested():
    """혼잡 TOP 10 역 데이터 로드 (캐싱)"""
    return pd.read_parquet("data/processed/top_congested.parquet")


@st.cache_data
def load_top_least_congested():
    """여유 TOP 10 역 데이터 로드 (캐싱)"""
    return pd.read_parquet("data/processed/top_least_congested.parquet")


@st.cache_data
def load_peak_times():
    """피크 시간대 데이터 로드 (캐싱)"""
    return pd.read_parquet("data/processed/peak_times.parquet")


def get_unique_values():
    """필터용 고유값 조회"""
    station_df = load_station_time_avg()
    
    return {
        'day_types': sorted(station_df['day_type'].unique()),
        'lines': sorted(station_df['line'].unique(), key=lambda x: int(x.replace('호선', ''))),
        'time_slots': sorted(station_df['time_slot'].unique())
    }


def create_sidebar_filters():
    """공통 사이드바 필터 생성"""
    st.sidebar.header("🔍 필터 설정")
    
    unique_vals = get_unique_values()
    
    # 요일 선택
    day_type = st.sidebar.selectbox(
        "요일 선택",
        options=unique_vals['day_types'],
        index=0
    )
    
    # 노선 선택 (멀티셀렉트)
    lines = st.sidebar.multiselect(
        "노선 선택",
        options=unique_vals['lines'],
        default=unique_vals['lines']
    )
    
    # 시간대 범위 슬라이더
    time_slots = unique_vals['time_slots']
    st.sidebar.subheader("시간대 범위")
    
    time_range = st.sidebar.slider(
        "시간대 선택",
        min_value=0,
        max_value=len(time_slots) - 1,
        value=(0, len(time_slots) - 1),
        format=""
    )
    
    # 선택된 시간대 표시
    selected_times = time_slots[time_range[0]:time_range[1]+1]
    st.sidebar.caption(f"선택: {time_slots[time_range[0]]} ~ {time_slots[time_range[1]]}")
    
    return {
        'day_type': day_type,
        'lines': lines,
        'time_range': (time_slots[time_range[0]], time_slots[time_range[1]]),
        'selected_times': selected_times
    }


def main():
    """메인 홈페이지"""
    st.title("🚇 서울교통공사 지하철 혼잡도 대시보드")
    
    # 사이드바 필터
    filters = create_sidebar_filters()
    
    # 세션 스테이트에 필터 저장 (다른 페이지에서 접근 가능)
    st.session_state['filters'] = filters
    
    st.markdown("---")
    
    # 소개
    st.markdown("""
    ## 📊 대시보드 소개
    
    이 대시보드는 서울교통공사 지하철(1~8호선)의 혼잡도 데이터를 시각화하여 제공합니다.
    
    ### 페이지 구성
    
    - **📈 Overview**: 전체 혼잡도 요약, TOP 10 혼잡 역, 노선별 평균 혼잡도
    - **🚉 Station Detail**: 특정 역의 시간대별 혼잡도 추이 및 인사이트
    - **🔥 Heatmap**: 시간대 × 노선 혼잡도 히트맵
    
    ### 혼잡도 등급 기준
    """)
    
    # 혼잡도 등급 표시
    cols = st.columns(4)
    levels = [
        ("여유", "0 ~ 30", CONGESTION_COLORS["여유"]),
        ("보통", "30 ~ 60", CONGESTION_COLORS["보통"]),
        ("혼잡", "60 ~ 90", CONGESTION_COLORS["혼잡"]),
        ("매우혼잡", "90 이상", CONGESTION_COLORS["매우혼잡"])
    ]
    
    for col, (level, range_text, color) in zip(cols, levels):
        col.markdown(
            f"""
            <div style="background-color: {color}; padding: 15px; border-radius: 5px; text-align: center;">
                <h3 style="color: white; margin: 0;">{level}</h3>
                <p style="color: white; margin: 5px 0 0 0;">{range_text}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # 현재 필터 상태 표시
    st.subheader("🎯 현재 필터 설정")
    
    filter_cols = st.columns(3)
    filter_cols[0].metric("요일", filters['day_type'])
    filter_cols[1].metric("선택된 노선 수", len(filters['lines']))
    filter_cols[2].metric("시간대 범위", f"{filters['time_range'][0]} ~ {filters['time_range'][1]}")
    
    st.info("👈 왼쪽 사이드바에서 필터를 조정하고, 상단 메뉴에서 원하는 페이지를 선택하세요!")


if __name__ == "__main__":
    main()
