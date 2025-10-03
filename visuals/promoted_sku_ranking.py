import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from itertools import cycle

def _prepare_df_basic(df: pd.DataFrame):
    """基础清洗：保证列存在并转换类型。"""
    df = df.copy()
    # 列名兼容性（你可以把实际列名换成你 DataFrame 的列名）
    # 假设用户的列名为 'Day','Promoted OMSID','SPA Sales_y'
    if 'Day' not in df.columns or 'Promoted OMSID' not in df.columns or 'SPA Sales_y' not in df.columns:
        missing = [c for c in ['Day','Promoted OMSID','SPA Sales_y'] if c not in df.columns]
        raise ValueError(f"缺少必需列: {missing}")

    # Day -> datetime
    df['Day'] = pd.to_datetime(df['Day'], errors='coerce')
    # Promoted OMSID -> str (填空避免 NaN)
    df['Promoted OMSID'] = df['Promoted OMSID'].fillna('').astype(str)
    # SPA Sales_y -> numeric (NaN -> 0)
    df['SPA Sales_y'] = pd.to_numeric(df['SPA Sales_y'], errors='coerce').fillna(0)
    return df

def _make_color_map(keys, palette=None):
    """为每个 key 分配颜色，返回 dict。"""
    if palette is None:
        palette = px.colors.qualitative.Plotly  # 默认调色板
    cmap = {}
    # 如果 keys 多于 palette，循环使用
    for k, c in zip(keys, cycle(palette)):
        cmap[k] = c
    return cmap

def plot_total_promoted_bars(df: pd.DataFrame, top_n: int = None, key: str = "promoted_bar"):
    """
    所有时间内按 Promoted OMSID 聚合 SPA Sales_y 并绘制 Top N 柱状图。
    返回 (top_promoted_list, color_map).
    """
    df = _prepare_df_basic(df)
    
    # 汇总
    df_grouped = (
        df.groupby('Promoted OMSID', as_index=False)['SPA Sales_y']
          .sum()
          .sort_values('SPA Sales_y', ascending=False)
    )
    
    # 默认 top_n 为 min(10, unique count)
    if top_n is None:
        top_n = min(10, len(df_grouped))

    # Streamlit 控件：可调整 Top N（也可以在外部传 top_n）
    top_n = st.slider("选择 Top N Promoted OMSID（按总销售）", min_value=1, max_value=max(1, len(df_grouped)), value=top_n, key=f"{key}_slider")

    df_top = df_grouped.head(top_n).copy()
    # 确保字符串型，并且用于 categoryaxis
    df_top['Promoted OMSID'] = df_top['Promoted OMSID'].astype(str)
    x_vals = df_top['Promoted OMSID'].tolist()
    y_vals = df_top['SPA Sales_y'].tolist()

    # 生成颜色映射（保证后续折线图用同一配色）
    color_map = _make_color_map(x_vals)

    # 柱状图：显式传入 x list 强制分类，并按给定顺序显示
    fig = px.bar(
        x=x_vals,
        y=y_vals,
        labels={'x': 'Promoted OMSID', 'y': 'Total SPA Sales'},
        text=y_vals,
        title=f"Top {top_n} Promoted OMSID by total SPA Sales (all time)"
    )
    fig.update_traces(textposition="outside")
    fig.update_xaxes(type='category', categoryorder='array', categoryarray=x_vals, tickangle=45, automargin=True)
    fig.update_layout(yaxis_title="Total SPA Sales", margin=dict(t=60, b=140))

    # 给每个 bar 指定颜色（按 x 顺序）
    for i, bar in enumerate(fig.data):
        # px.bar 当 x 是 list 时只有一个 trace，直接更新 marker.colors
        pass
    # 更简单：构造单一颜色列表并设置到第一个 trace
    colors = [color_map[x] for x in x_vals]
    if fig.data:
        fig.data[0].marker.color = colors

    st.plotly_chart(fig, use_container_width=True, key=f"{key}_fig")
    
    if 'HD SKU Map' in st.session_state.get('uploaded_data', {}):

        hd_map = st.session_state['uploaded_data']['HD SKU Map'].copy()
        # 确保两边都是字符串，避免匹配失败
        hd_map['OMSID'] = hd_map['OMSID'].astype(str)
        df_top['Promoted OMSID'] = df_top['Promoted OMSID'].astype(str)

        # 左连接：df_top 保留 Top N 行，带上对应 OMSID 信息
        df_display = df_top.merge(
            hd_map,
            left_on='Promoted OMSID',
            right_on='OMSID',
            how='left',
            suffixes=('', '_HDMap')
        )
    else:
        df_display = df_top.copy()

    st.dataframe(df_display.reset_index(drop=True), use_container_width=True)

    return x_vals, color_map


def plot_promoted_daily_lines(df: pd.DataFrame, promoted_list: list, color_map: dict, fill_zero: bool = True, key: str = "promoted_lines"):
    """
    对指定的 promoted_list（Promoted OMSID 列表）按 Day 聚合每天的 SPA Sales_y（缺失日期填0），
    并画折线图。color_map 用于保持颜色一致（key=Promoted OMSID -> color）。
    """
    df = _prepare_df_basic(df)

    # 只保留我们关心的 promoted_list
    df_sel = df[df['Promoted OMSID'].isin(promoted_list)].copy()

    # 按 Day + Promoted 聚合
    daily = df_sel.groupby(['Day','Promoted OMSID'], as_index=False)['SPA Sales_y'].sum()

    # 构造完整日期索引（从数据最早到最新）
    if daily['Day'].isnull().all():
        st.warning("没有有效的 Day 日期可用于绘制折线图。")
        return
    min_day = daily['Day'].min()
    max_day = daily['Day'].max()
    full_idx = pd.date_range(start=min_day.normalize(), end=max_day.normalize(), freq='D')

    # pivot 为 wide 表：index=Day, columns=Promoted OMSID
    pivot = daily.pivot_table(index='Day', columns='Promoted OMSID', values='SPA Sales_y', aggfunc='sum').reindex(full_idx).rename_axis('Day')
    # 填充缺失
    if fill_zero:
        pivot = pivot.fillna(0)
    else:
        pivot = pivot.fillna(0)

    # 如果某些 promoted 在 promoted_list 但 pivot 没有该列（可能在选择时间内无数据），添加列并填0
    for p in promoted_list:
        if p not in pivot.columns and p in color_map:
            pivot[p] = 0

    # 保证列顺序与 promoted_list 一致
    pivot = pivot.reindex(columns=promoted_list)

    # 将宽表展开为长表供 px.line 使用
    long = pivot.reset_index().melt(id_vars='Day', var_name='Promoted OMSID', value_name='SPA Sales_y')

    # 强制 Promoted OMSID 为 str (以匹配 color_map keys)
    long['Promoted OMSID'] = long['Promoted OMSID'].astype(str)

    # 绘制折线图，使用 color_discrete_map 保持每个 promoted 的颜色一致
    fig = px.line(
        long,
        x='Day',
        y='SPA Sales_y',
        color='Promoted OMSID',
        color_discrete_map=color_map,
        title="Daily SPA Sales by Promoted OMSID"
    )

    fig.update_traces(mode='lines+markers', hovertemplate='Promoted: %{legendgroup}<br>Date: %{x|%Y-%m-%d}<br>Sales: %{y}')
    fig.update_layout(xaxis=dict(tickformat='%Y-%m-%d', tickangle=45, nticks=20), margin=dict(t=50, b=120), yaxis_title='Daily SPA Sales')

    st.plotly_chart(fig, use_container_width=True, key=f"{key}_fig")
