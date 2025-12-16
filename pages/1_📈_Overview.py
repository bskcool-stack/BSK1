"""
페이지 1: Overview (요약)

전체 혼잡도 요약, TOP 10 혼잡 역, 노선별 평균 혼잡도
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.viz import create_line_bar_chart, create_kpi_card, CONGESTION_COLORS
from src.metrics import get_congestion_level

# 페이지 설정
st.set_page_config(
    page_title="Overview - 지하철 혼잡도",
    page_icon="📈",
    layout="wide"
)


@st.cache_data
def load_data():
    """데이터 로드"""
    return {
        'line_time_avg': pd.read_parquet("data/processed/line_time_avg.parquet"),
        'station_time_avg': pd.read_parquet("data/processed/station_time_avg.parquet"),
        'top_congested': pd.read_parquet("data/processed/top_congested.parquet"),
        'top_least_congested': pd.read_parquet("data/processed/top_least_congested.parquet")
    }


def main():
    st.title("📈 Overview - 혼잡도 요약")
    
    # 세션 스테이트에서 필터 가져오기
    if 'filters' not in st.session_state:
        st.warning("필터를 설정하려면 메인 페이지로 이동하세요.")
        filters = {
            'day_type': '평일',
            'lines': [],
            'time_range': ('05:30', '00:30'),
            'selected_times': []
        }
    else:
        filters = st.session_state['filters']
    
    # 데이터 로드
    data = load_data()
    
    st.markdown("---")
    
    # === KPI 카드 영역 ===
    st.subheader("🎯 주요 지표")
    
    # 필터 적용
    station_df = data['station_time_avg']
    filtered_station = station_df[station_df['day_type'] == filters['day_type']].copy()
    
    if filters['lines']:
        filtered_station = filtered_station[filtered_station['line'].isin(filters['lines'])]
    
    if filters['selected_times']:
        filtered_station = filtered_station[filtered_station['time_slot'].isin(filters['selected_times'])]
    
    # KPI 계산
    if not filtered_station.empty:
        avg_congestion = filtered_station['avg_congestion'].mean()
        most_congested = filtered_station.loc[filtered_station['avg_congestion'].idxmax()]
        least_congested_filtered = filtered_station[filtered_station['avg_congestion'] > 0]
        
        if not least_congested_filtered.empty:
            least_congested = least_congested_filtered.loc[least_congested_filtered['avg_congestion'].idxmin()]
        else:
            least_congested = None
        
        # KPI 카드 표시
        cols = st.columns(3)
        
        with cols[0]:
            avg_level = get_congestion_level(avg_congestion)
            st.markdown(
                create_kpi_card(
                    "평균 혼잡도",
                    f"{avg_congestion:.1f}",
                    CONGESTION_COLORS[avg_level]
                ),
                unsafe_allow_html=True
            )
        
        with cols[1]:
            most_level = get_congestion_level(most_congested['avg_congestion'])
            st.markdown(
                create_kpi_card(
                    "가장 혼잡한 역",
                    f"{most_congested['station_name']}<br>({most_congested['avg_congestion']:.1f})",
                    CONGESTION_COLORS[most_level]
                ),
                unsafe_allow_html=True
            )
        
        with cols[2]:
            if least_congested is not None:
                least_level = get_congestion_level(least_congested['avg_congestion'])
                st.markdown(
                    create_kpi_card(
                        "가장 여유로운 역",
                        f"{least_congested['station_name']}<br>({least_congested['avg_congestion']:.1f})",
                        CONGESTION_COLORS[least_level]
                    ),
                    unsafe_allow_html=True
                )
    else:
        st.info("선택한 조건에 맞는 데이터가 없습니다.")
    
    st.markdown("---")
    
    # === 혼잡 TOP 10 테이블 ===
    st.subheader("🔥 혼잡 TOP 10 역")
    
    top_congested = data['top_congested']
    top_congested_filtered = top_congested[
        top_congested['day_type'] == filters['day_type']
    ].copy()
    
    if not top_congested_filtered.empty:
        # 표시할 컬럼 선택
        display_df = top_congested_filtered[
            ['rank', 'station_name', 'line', 'direction', 'avg_congestion']
        ].copy()
        
        display_df.columns = ['순위', '역명', '노선', '방향', '평균 혼잡도']
        display_df['혼잡도 등급'] = display_df['평균 혼잡도'].apply(get_congestion_level)
        
        # 스타일링 함수
        def style_row(row):
            level = get_congestion_level(row['평균 혼잡도'])
            color = CONGESTION_COLORS[level]
            return [
                '',  # 순위
                '',  # 역명
                '',  # 노선
                '',  # 방향
                f'background-color: {color}; color: white; font-weight: bold;',  # 평균 혼잡도
                f'background-color: {color}; color: white; font-weight: bold;'   # 혼잡도 등급
            ]
        
        styled_df = display_df.style.apply(style_row, axis=1)
        
        st.dataframe(styled_df, use_container_width=True, height=400)
    else:
        st.info("표시할 데이터가 없습니다.")
    
    st.markdown("---")
    
    # === 노선별 평균 혼잡도 막대그래프 ===
    st.subheader("🚇 노선별 평균 혼잡도")
    
    line_time_df = data['line_time_avg']
    
    # 필터 적용
    filtered_line = line_time_df[line_time_df['day_type'] == filters['day_type']].copy()
    
    if filters['selected_times']:
        filtered_line = filtered_line[filtered_line['time_slot'].isin(filters['selected_times'])]
    
    if not filtered_line.empty:
        fig = create_line_bar_chart(
            filtered_line,
            filters['day_type'],
            filters['lines'] if filters['lines'] else None
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("선택한 조건에 맞는 데이터가 없습니다.")
    
    st.markdown("---")
    
    # === 여유 TOP 10 역 (추가) ===
    with st.expander("✅ 여유 TOP 10 역 보기"):
        top_least = data['top_least_congested']
        top_least_filtered = top_least[
            top_least['day_type'] == filters['day_type']
        ].copy()
        
        if not top_least_filtered.empty:
            display_df = top_least_filtered[
                ['rank', 'station_name', 'line', 'direction', 'avg_congestion']
            ].copy()
            
            display_df.columns = ['순위', '역명', '노선', '방향', '평균 혼잡도']
            display_df['혼잡도 등급'] = display_df['평균 혼잡도'].apply(get_congestion_level)
            
            def style_row(row):
                level = get_congestion_level(row['평균 혼잡도'])
                color = CONGESTION_COLORS[level]
                return [
                    '',  # 순위
                    '',  # 역명
                    '',  # 노선
                    '',  # 방향
                    f'background-color: {color}; color: white; font-weight: bold;',
                    f'background-color: {color}; color: white; font-weight: bold;'
                ]
            
            styled_df = display_df.style.apply(style_row, axis=1)
            
            st.dataframe(styled_df, use_container_width=True, height=400)


if __name__ == "__main__":
    main()

