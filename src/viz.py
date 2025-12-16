"""
시각화 함수 모듈 (Phase 3)

Streamlit 대시보드에서 사용할 차트 생성 함수들
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional
import streamlit as st

# 혼잡도 등급별 색상 매핑
CONGESTION_COLORS = {
    "여유": "#28a745",
    "보통": "#ffc107",
    "혼잡": "#fd7e14",
    "매우혼잡": "#dc3545"
}

# 연속적인 색상 스케일 (히트맵용)
HEATMAP_COLORSCALE = [
    [0.0, "#28a745"],   # 여유 (녹색)
    [0.33, "#ffc107"],  # 보통 (노랑)
    [0.67, "#fd7e14"],  # 혼잡 (주황)
    [1.0, "#dc3545"]    # 매우혼잡 (빨강)
]


def create_line_bar_chart(df: pd.DataFrame, day_type: str, lines: list = None) -> go.Figure:
    """
    노선별 평균 혼잡도 막대그래프
    
    Parameters
    ----------
    df : pd.DataFrame
        line_time_avg 데이터프레임
    day_type : str
        요일 구분 (평일/토요일/일요일)
    lines : list, optional
        표시할 노선 리스트 (None이면 전체)
    
    Returns
    -------
    go.Figure
        Plotly 막대 차트
    """
    # 요일 필터링
    filtered_df = df[df['day_type'] == day_type].copy()
    
    # 노선 필터링
    if lines:
        filtered_df = filtered_df[filtered_df['line'].isin(lines)]
    
    # 노선별 평균 계산
    line_avg = filtered_df.groupby('line', as_index=False)['avg_congestion'].mean()
    
    # 노선 정렬 (숫자 순서)
    line_avg['line_num'] = line_avg['line'].str.replace('호선', '').astype(int)
    line_avg = line_avg.sort_values('line_num')
    
    # 혼잡도 등급별 색상 적용
    def get_color(congestion):
        if congestion < 30:
            return CONGESTION_COLORS["여유"]
        elif congestion < 60:
            return CONGESTION_COLORS["보통"]
        elif congestion < 90:
            return CONGESTION_COLORS["혼잡"]
        else:
            return CONGESTION_COLORS["매우혼잡"]
    
    line_avg['color'] = line_avg['avg_congestion'].apply(get_color)
    
    # 막대 차트 생성
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=line_avg['avg_congestion'],
        y=line_avg['line'],
        orientation='h',
        marker=dict(
            color=line_avg['color'],
            line=dict(color='rgba(0,0,0,0.3)', width=1)
        ),
        text=line_avg['avg_congestion'].round(1),
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>평균 혼잡도: %{x:.1f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=f"{day_type} 노선별 평균 혼잡도",
        xaxis_title="평균 혼잡도",
        yaxis_title="",
        height=400,
        showlegend=False,
        hovermode='closest',
        margin=dict(l=100, r=50, t=50, b=50)
    )
    
    return fig


def create_station_line_chart(
    df: pd.DataFrame,
    station: str,
    day_type: str,
    time_range: tuple = None
) -> go.Figure:
    """
    역의 시간대별 혼잡도 라인차트 (상/하행 비교)
    
    Parameters
    ----------
    df : pd.DataFrame
        station_time_avg 데이터프레임
    station : str
        역명
    day_type : str
        요일 구분
    time_range : tuple, optional
        시간대 범위 (시작시간, 종료시간)
    
    Returns
    -------
    go.Figure
        Plotly 라인 차트
    """
    # 필터링
    filtered_df = df[
        (df['station_name'] == station) &
        (df['day_type'] == day_type)
    ].copy()
    
    # 시간대 범위 필터링
    if time_range:
        filtered_df = filtered_df[
            (filtered_df['time_slot'] >= time_range[0]) &
            (filtered_df['time_slot'] <= time_range[1])
        ]
    
    if filtered_df.empty:
        # 데이터가 없을 경우 빈 차트 반환
        fig = go.Figure()
        fig.add_annotation(
            text="선택한 조건에 맞는 데이터가 없습니다.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig
    
    # 방향별로 라인 추가
    fig = go.Figure()
    
    directions = filtered_df['direction'].unique()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']  # 방향별 색상
    
    for i, direction in enumerate(directions):
        direction_df = filtered_df[filtered_df['direction'] == direction].sort_values('time_slot')
        
        fig.add_trace(go.Scatter(
            x=direction_df['time_slot'],
            y=direction_df['avg_congestion'],
            mode='lines+markers',
            name=direction,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=6),
            hovertemplate='<b>%{x}</b><br>혼잡도: %{y:.1f}<extra></extra>'
        ))
    
    # 혼잡도 등급 배경 영역 추가
    fig.add_hrect(y0=0, y1=30, fillcolor="green", opacity=0.1, line_width=0)
    fig.add_hrect(y0=30, y1=60, fillcolor="yellow", opacity=0.1, line_width=0)
    fig.add_hrect(y0=60, y1=90, fillcolor="orange", opacity=0.1, line_width=0)
    fig.add_hrect(y0=90, y1=200, fillcolor="red", opacity=0.1, line_width=0)
    
    fig.update_layout(
        title=f"{station} - {day_type} 시간대별 혼잡도",
        xaxis_title="시간대",
        yaxis_title="혼잡도",
        height=450,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # x축 레이블 회전
    fig.update_xaxes(tickangle=-45)
    
    return fig


def create_heatmap(
    df: pd.DataFrame,
    day_type: str,
    lines: list = None,
    time_range: tuple = None
) -> go.Figure:
    """
    시간대 × 노선 혼잡도 히트맵
    
    Parameters
    ----------
    df : pd.DataFrame
        line_time_avg 데이터프레임
    day_type : str
        요일 구분
    lines : list, optional
        표시할 노선 리스트
    time_range : tuple, optional
        시간대 범위
    
    Returns
    -------
    go.Figure
        Plotly 히트맵
    """
    # 필터링
    filtered_df = df[df['day_type'] == day_type].copy()
    
    if lines:
        filtered_df = filtered_df[filtered_df['line'].isin(lines)]
    
    if time_range:
        filtered_df = filtered_df[
            (filtered_df['time_slot'] >= time_range[0]) &
            (filtered_df['time_slot'] <= time_range[1])
        ]
    
    # 피벗 테이블 생성 (노선 × 시간대)
    pivot_df = filtered_df.pivot_table(
        index='line',
        columns='time_slot',
        values='avg_congestion',
        aggfunc='mean'
    )
    
    # 노선 정렬 (숫자 순서)
    pivot_df['line_num'] = pivot_df.index.str.replace('호선', '').astype(int)
    pivot_df = pivot_df.sort_values('line_num').drop('line_num', axis=1)
    
    # 히트맵 생성
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale=HEATMAP_COLORSCALE,
        hovertemplate='노선: %{y}<br>시간대: %{x}<br>혼잡도: %{z:.1f}<extra></extra>',
        colorbar=dict(
            title="혼잡도",
            tickvals=[0, 30, 60, 90, 120],
            ticktext=["0 (여유)", "30", "60", "90", "120+"]
        )
    ))
    
    fig.update_layout(
        title=f"{day_type} 시간대별 노선 혼잡도 히트맵",
        xaxis_title="시간대",
        yaxis_title="노선",
        height=500,
        xaxis=dict(tickangle=-45)
    )
    
    return fig


def style_congestion_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    혼잡도 테이블에 색상 스타일 적용
    
    Parameters
    ----------
    df : pd.DataFrame
        표시할 데이터프레임
    
    Returns
    -------
    pd.DataFrame.style
        스타일이 적용된 데이터프레임
    """
    def color_congestion(val):
        """혼잡도 값에 따른 배경색 반환"""
        if pd.isna(val):
            return ''
        
        if val < 30:
            color = CONGESTION_COLORS["여유"]
        elif val < 60:
            color = CONGESTION_COLORS["보통"]
        elif val < 90:
            color = CONGESTION_COLORS["혼잡"]
        else:
            color = CONGESTION_COLORS["매우혼잡"]
        
        return f'background-color: {color}; color: white; font-weight: bold;'
    
    # 혼잡도 컬럼에만 스타일 적용
    congestion_cols = [col for col in df.columns if 'congestion' in col.lower()]
    
    if congestion_cols:
        styled_df = df.style.applymap(
            color_congestion,
            subset=congestion_cols
        )
        return styled_df
    
    return df


def create_kpi_card(label: str, value: str, color: str = "#1f77b4"):
    """
    KPI 카드 HTML 생성
    
    Parameters
    ----------
    label : str
        라벨
    value : str
        값
    color : str
        배경색
    
    Returns
    -------
    str
        HTML 문자열
    """
    return f"""
    <div style="background-color: {color}; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
        <h4 style="color: white; margin: 0; font-size: 14px;">{label}</h4>
        <h2 style="color: white; margin: 10px 0 0 0; font-size: 28px;">{value}</h2>
    </div>
    """

