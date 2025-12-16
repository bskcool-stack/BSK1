"""
페이지 3: Heatmap (히트맵)

시간대 × 노선 혼잡도 히트맵
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.viz import create_heatmap, CONGESTION_COLORS
from src.metrics import get_congestion_level

# 페이지 설정
st.set_page_config(
    page_title="Heatmap - 지하철 혼잡도",
    page_icon="🔥",
    layout="wide"
)


@st.cache_data
def load_data():
    """데이터 로드"""
    return pd.read_parquet("data/processed/line_time_avg.parquet")


def main():
    st.title("🔥 Heatmap - 시간대별 혼잡도 히트맵")
    
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
    line_time_df = load_data()
    
    st.markdown("---")
    
    # === 히트맵 설명 ===
    st.info(
        """
        📌 **히트맵 사용법**
        - **색상**: 녹색(여유) → 노랑(보통) → 주황(혼잡) → 빨강(매우혼잡)
        - **X축**: 시간대 (05:30 ~ 00:30)
        - **Y축**: 노선 (1~8호선)
        - **마우스 호버**: 세부 정보 확인
        """
    )
    
    st.markdown("---")
    
    # === 히트맵 생성 ===
    st.subheader(f"🗺️ {filters['day_type']} 시간대별 노선 혼잡도")
    
    # 필터 적용된 히트맵 생성
    fig = create_heatmap(
        line_time_df,
        filters['day_type'],
        filters['lines'] if filters['lines'] else None,
        filters['time_range']
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # === 시간대별 통계 ===
    st.subheader("📊 시간대별 통계")
    
    # 필터 적용
    filtered_df = line_time_df[line_time_df['day_type'] == filters['day_type']].copy()
    
    if filters['lines']:
        filtered_df = filtered_df[filtered_df['line'].isin(filters['lines'])]
    
    if filters['selected_times']:
        filtered_df = filtered_df[filtered_df['time_slot'].isin(filters['selected_times'])]
    
    if not filtered_df.empty:
        # 시간대별 평균 계산
        time_stats = filtered_df.groupby('time_slot').agg({
            'avg_congestion': ['mean', 'max', 'min']
        }).round(1)
        
        time_stats.columns = ['평균', '최대', '최소']
        time_stats = time_stats.reset_index()
        time_stats.columns = ['시간대', '평균 혼잡도', '최대 혼잡도', '최소 혼잡도']
        
        # 혼잡도 등급 추가
        time_stats['등급'] = time_stats['평균 혼잡도'].apply(get_congestion_level)
        
        # 스타일링
        def style_congestion_cols(val):
            if pd.isna(val):
                return ''
            level = get_congestion_level(val)
            color = CONGESTION_COLORS[level]
            return f'background-color: {color}; color: white; font-weight: bold;'
        
        styled_df = time_stats.style.applymap(
            style_congestion_cols,
            subset=['평균 혼잡도', '최대 혼잡도', '최소 혼잡도']
        )
        
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # CSV 다운로드
        csv = time_stats.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 시간대별 통계 CSV 다운로드",
            data=csv,
            file_name=f"시간대별통계_{filters['day_type']}.csv",
            mime="text/csv"
        )
    else:
        st.info("선택한 조건에 맞는 데이터가 없습니다.")
    
    st.markdown("---")
    
    # === 노선별 통계 ===
    st.subheader("🚇 노선별 통계")
    
    if not filtered_df.empty:
        # 노선별 평균 계산
        line_stats = filtered_df.groupby('line').agg({
            'avg_congestion': ['mean', 'max', 'min', 'std']
        }).round(1)
        
        line_stats.columns = ['평균', '최대', '최소', '표준편차']
        line_stats = line_stats.reset_index()
        line_stats.columns = ['노선', '평균 혼잡도', '최대 혼잡도', '최소 혼잡도', '표준편차']
        
        # 노선 정렬
        line_stats['line_num'] = line_stats['노선'].str.replace('호선', '').astype(int)
        line_stats = line_stats.sort_values('line_num').drop('line_num', axis=1)
        
        # 혼잡도 등급 추가
        line_stats['등급'] = line_stats['평균 혼잡도'].apply(get_congestion_level)
        
        # 스타일링
        styled_df = line_stats.style.applymap(
            style_congestion_cols,
            subset=['평균 혼잡도', '최대 혼잡도', '최소 혼잡도', '표준편차']
        )
        
        st.dataframe(styled_df, use_container_width=True)
        
        # CSV 다운로드
        csv = line_stats.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 노선별 통계 CSV 다운로드",
            data=csv,
            file_name=f"노선별통계_{filters['day_type']}.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    
    # === 피크 시간대 분석 ===
    with st.expander("⏰ 피크 시간대 분석"):
        if not filtered_df.empty:
            # 가장 혼잡한 시간대 TOP 5
            st.subheader("🔴 가장 혼잡한 시간대 TOP 5")
            
            top_5_congested = filtered_df.nlargest(5, 'avg_congestion')[
                ['time_slot', 'line', 'avg_congestion', 'congestion_level']
            ].copy()
            top_5_congested.columns = ['시간대', '노선', '평균 혼잡도', '등급']
            
            for idx, row in top_5_congested.iterrows():
                color = CONGESTION_COLORS[row['등급']]
                st.markdown(
                    f"""
                    <div style="background-color: {color}; padding: 10px; border-radius: 5px; margin-bottom: 5px;">
                        <span style="color: white; font-weight: bold;">{row['시간대']}</span> - 
                        <span style="color: white;">{row['노선']}</span> - 
                        <span style="color: white;">{row['평균 혼잡도']:.1f}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            st.markdown("---")
            
            # 가장 여유로운 시간대 TOP 5
            st.subheader("🟢 가장 여유로운 시간대 TOP 5")
            
            # 0값 제외
            filtered_df_nonzero = filtered_df[filtered_df['avg_congestion'] > 0]
            
            if not filtered_df_nonzero.empty:
                top_5_least = filtered_df_nonzero.nsmallest(5, 'avg_congestion')[
                    ['time_slot', 'line', 'avg_congestion', 'congestion_level']
                ].copy()
                top_5_least.columns = ['시간대', '노선', '평균 혼잡도', '등급']
                
                for idx, row in top_5_least.iterrows():
                    color = CONGESTION_COLORS[row['등급']]
                    st.markdown(
                        f"""
                        <div style="background-color: {color}; padding: 10px; border-radius: 5px; margin-bottom: 5px;">
                            <span style="color: white; font-weight: bold;">{row['시간대']}</span> - 
                            <span style="color: white;">{row['노선']}</span> - 
                            <span style="color: white;">{row['평균 혼잡도']:.1f}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


if __name__ == "__main__":
    main()

