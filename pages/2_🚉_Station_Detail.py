"""
페이지 2: Station Detail (역 상세)

특정 역의 시간대별 혼잡도 추이 및 인사이트
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.viz import create_station_line_chart, CONGESTION_COLORS
from src.metrics import get_congestion_level

# 페이지 설정
st.set_page_config(
    page_title="Station Detail - 지하철 혼잡도",
    page_icon="🚉",
    layout="wide"
)


@st.cache_data
def load_data():
    """데이터 로드"""
    return {
        'station_time_avg': pd.read_parquet("data/processed/station_time_avg.parquet"),
        'peak_times': pd.read_parquet("data/processed/peak_times.parquet")
    }


def main():
    st.title("🚉 Station Detail - 역 상세 분석")
    
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
    station_df = data['station_time_avg']
    peak_df = data['peak_times']
    
    st.markdown("---")
    
    # === 역 선택 필터 ===
    st.subheader("🔍 역 선택")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 노선 선택
        available_lines = sorted(
            station_df['line'].unique(),
            key=lambda x: int(x.replace('호선', ''))
        )
        
        selected_line = st.selectbox(
            "노선 선택",
            options=available_lines,
            index=0
        )
    
    with col2:
        # 역명 선택 (선택된 노선의 역만 표시)
        available_stations = sorted(
            station_df[station_df['line'] == selected_line]['station_name'].unique()
        )
        
        selected_station = st.selectbox(
            "역 선택",
            options=available_stations,
            index=0
        )
    
    st.markdown("---")
    
    # === 시간대별 혼잡도 라인차트 ===
    st.subheader(f"📊 {selected_station} 시간대별 혼잡도")
    
    # 차트 생성
    fig = create_station_line_chart(
        station_df,
        selected_station,
        filters['day_type'],
        filters['time_range']
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # === 인사이트 패널 ===
    st.subheader("💡 인사이트")
    
    # 해당 역의 피크 정보 조회
    peak_info = peak_df[
        (peak_df['station_name'] == selected_station) &
        (peak_df['line'] == selected_line) &
        (peak_df['day_type'] == filters['day_type'])
    ]
    
    if not peak_info.empty:
        # 방향별로 표시
        for idx, row in peak_info.iterrows():
            with st.expander(f"📍 {row['direction']}", expanded=True):
                cols = st.columns(4)
                
                # 피크 시간대
                with cols[0]:
                    peak_level = get_congestion_level(row['peak_congestion'])
                    st.markdown(
                        f"""
                        <div style="background-color: {CONGESTION_COLORS[peak_level]}; padding: 15px; border-radius: 5px; text-align: center;">
                            <h5 style="color: white; margin: 0;">피크 시간대</h5>
                            <h3 style="color: white; margin: 5px 0;">{row['peak_time']}</h3>
                            <p style="color: white; margin: 0; font-size: 18px;">{row['peak_congestion']:.1f}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # 최저 혼잡 시간대
                with cols[1]:
                    least_level = get_congestion_level(row['least_congestion'])
                    st.markdown(
                        f"""
                        <div style="background-color: {CONGESTION_COLORS[least_level]}; padding: 15px; border-radius: 5px; text-align: center;">
                            <h5 style="color: white; margin: 0;">최저 혼잡 시간</h5>
                            <h3 style="color: white; margin: 5px 0;">{row['least_time']}</h3>
                            <p style="color: white; margin: 0; font-size: 18px;">{row['least_congestion']:.1f}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # 평균 혼잡도
                with cols[2]:
                    avg_level = get_congestion_level(row['avg_congestion'])
                    st.markdown(
                        f"""
                        <div style="background-color: {CONGESTION_COLORS[avg_level]}; padding: 15px; border-radius: 5px; text-align: center;">
                            <h5 style="color: white; margin: 0;">평균 혼잡도</h5>
                            <h3 style="color: white; margin: 5px 0;">{row['avg_congestion']:.1f}</h3>
                            <p style="color: white; margin: 0; font-size: 14px;">{avg_level}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # 변동성
                with cols[3]:
                    variance = row['variance']
                    std = variance ** 0.5
                    
                    # 변동성 평가
                    if std < 10:
                        var_level = "낮음"
                        var_color = "#28a745"
                    elif std < 20:
                        var_level = "보통"
                        var_color = "#ffc107"
                    else:
                        var_level = "높음"
                        var_color = "#dc3545"
                    
                    st.markdown(
                        f"""
                        <div style="background-color: {var_color}; padding: 15px; border-radius: 5px; text-align: center;">
                            <h5 style="color: white; margin: 0;">혼잡도 변동성</h5>
                            <h3 style="color: white; margin: 5px 0;">{std:.1f}</h3>
                            <p style="color: white; margin: 0; font-size: 14px;">{var_level}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                st.markdown("---")
                
                # 추천 메시지
                if row['least_congestion'] < 30:
                    st.success(
                        f"✅ **추천**: {row['least_time']}에 이용하시면 여유롭게 탑승할 수 있습니다! (혼잡도: {row['least_congestion']:.1f})"
                    )
                
                if row['peak_congestion'] > 90:
                    st.error(
                        f"⚠️ **주의**: {row['peak_time']}는 매우 혼잡합니다. 가능하면 다른 시간대 이용을 권장합니다. (혼잡도: {row['peak_congestion']:.1f})"
                    )
    else:
        st.info("선택한 역의 피크 정보를 찾을 수 없습니다.")
    
    st.markdown("---")
    
    # === 방향별 비교 테이블 ===
    st.subheader("📋 시간대별 상세 데이터")
    
    # 선택된 역의 데이터 필터링
    detail_df = station_df[
        (station_df['station_name'] == selected_station) &
        (station_df['line'] == selected_line) &
        (station_df['day_type'] == filters['day_type'])
    ].copy()
    
    if filters['selected_times']:
        detail_df = detail_df[detail_df['time_slot'].isin(filters['selected_times'])]
    
    if not detail_df.empty:
        # 피벗 테이블 (시간대 × 방향)
        pivot_df = detail_df.pivot_table(
            index='time_slot',
            columns='direction',
            values='avg_congestion',
            aggfunc='mean'
        ).round(1)
        
        # 스타일링
        def color_value(val):
            if pd.isna(val):
                return ''
            level = get_congestion_level(val)
            color = CONGESTION_COLORS[level]
            return f'background-color: {color}; color: white; font-weight: bold;'
        
        styled_df = pivot_df.style.applymap(color_value)
        
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # CSV 다운로드 버튼
        csv = detail_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv,
            file_name=f"{selected_station}_{filters['day_type']}_혼잡도.csv",
            mime="text/csv"
        )
    else:
        st.info("표시할 데이터가 없습니다.")


if __name__ == "__main__":
    main()

