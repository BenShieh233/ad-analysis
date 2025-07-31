import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def plot_dual_metric_trends(
    df,
    metrics,
    date_col,
    campaign_col,
    ad_type_col,
    mean_metrics
):
    """
    在 Tab3 中绘制共轴双指标趋势图，复用已选的 selected_campaign。
    - df: 原始 DataFrame
    - metrics: 全部指标列表
    - date_col: 时间列
    - campaign_col: Campaign ID 列
    - ad_type_col: 广告类型列
    - mean_metrics: 以均值计算排名的指标列表
    """
    selected_campaign = st.session_state.get("tab3_campaign")
    if not selected_campaign:
        st.warning("请先选择 Campaign ID")
        return

    # 选择指标
    col1, col2 = st.columns(2)
    with col1:
        metric1 = st.selectbox("选择第一个对比指标", options=metrics, key="dual_metric1")
    with col2:
        options2 = [m for m in metrics if m != metric1]
        metric2 = st.selectbox("选择第二个对比指标", options=options2, key="dual_metric2")

    # 计算排名
    ranks = {}
    for m in (metric1, metric2):
        vals = df.groupby(campaign_col)[m].mean() if m in mean_metrics else df.groupby(campaign_col)[m].sum()
        sorted_ids = vals.sort_values(ascending=False).index.tolist()
        ranks[m] = sorted_ids.index(selected_campaign) + 1

    # 准备趋势数据
    sel_df = df[df[campaign_col] == selected_campaign].sort_values(date_col)
    x = sel_df[date_col]
    y1 = sel_df[metric1]
    y2 = sel_df[metric2]

    # 绘图
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y1, mode="lines+markers",
                              name=f"{metric1} (Rank {ranks[metric1]})", yaxis="y1"))
    fig.add_trace(go.Scatter(x=x, y=y2, mode="lines+markers",
                              name=f"{metric2} (Rank {ranks[metric2]})", yaxis="y2"))
    fig.update_layout(
        title=f"Campaign {selected_campaign} 指标对比趋势",
        xaxis_title=date_col,
        yaxis=dict(title=metric1, side="left"),
        yaxis2=dict(title=metric2, overlaying="y", side="right"),
        template="plotly_white",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 显示选中 Campaign 在所有指标的聚合值（总和或均值）
    # 计算各指标值
    agg_vals = {}
    for m in metrics:
        sub = df[df[campaign_col] == selected_campaign]
        val = sub[m].mean() if m in mean_metrics else sub[m].sum()
        agg_vals[m] = val
    # 显示表格
    st.write(f"Campaign {selected_campaign} 聚合指标值")
    df_table = pd.DataFrame.from_dict(agg_vals, orient='index', columns=['值'])
    df_table.index.name = '指标'
    st.table(df_table)

def plot_campaign_radar_ranks(
    df,
    metrics,
    campaign_col,
    mean_metrics
):
    """
    使用雷达图展示 selected_campaign 在所有指标的排名。
    - df: 原始 DataFrame
    - metrics: 所有指标列表
    - campaign_col: Campaign ID 列
    - mean_metrics: 以均值计算排名的指标列表
    """
    selected_campaign = st.session_state.get("tab3_campaign")
    if not selected_campaign:
        st.warning("请先选择 Campaign ID")
        return

    # 计算排名列表
    ranks = []
    for m in metrics:
        vals = df.groupby(campaign_col)[m].mean() if m in mean_metrics else df.groupby(campaign_col)[m].sum()
        sorted_ids = vals.sort_values(ascending=False).index.tolist()
        ranks.append(sorted_ids.index(selected_campaign) + 1)

    # 闭合
    categories = metrics + [metrics[0]]
    values = ranks + [ranks[0]]

    fig = go.Figure()
    # 绘制 selected_campaign 排名
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            mode='lines+markers+text',
            text=[str(v) for v in values],
            textposition='top center',
            name=f"{selected_campaign} 排名"
        )
    )

    # 更新布局
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                autorange='reversed',
            )
        ),
        showlegend=True,
        title=f"Campaign {selected_campaign} 指标排名雷达图"
    )
    st.plotly_chart(fig, use_container_width=True)
