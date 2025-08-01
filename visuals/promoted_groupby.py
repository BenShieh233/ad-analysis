import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_promoted_sku_rank(
    df_promoted: pd.DataFrame,
    selected_campaign: str,
    metrics: list[str],
    sku_col: str = 'Promoted OMSID',
):
    """
    在 Tab3 或 Tab4 中：
    1. 对选定 Campaign 内各 SKU 除 'SPA ROAS' 外的指标做 sum 聚合；
    2. 打印聚合表格，并基于 SPA Sales / Spend 计算 SPA ROAS；
    3. 对每个除 SPA ROAS 外的指标绘制饼图，展示各 SKU 在该指标中的占比。
    """

    df_p = df_promoted.copy()

    # 1. 聚合各 SKU 指标
    agg_dict = {}
    for m in metrics:
        agg_dict[m] = df_p.groupby(sku_col)[m].sum()
    df_agg = pd.DataFrame(agg_dict)

    # 2. 计算 SPA ROAS
    df_agg['SPA ROAS'] = df_agg['SPA Sales'] / df_agg['Spend']

    # 3. 如果有映射列，合并映射信息
    mapping_cols = ["MFG Model #", "OMS THD SKU", "Product Name (120)"]
    # 检查是否在原始 df 中都有
    if all(col in df_p.columns for col in mapping_cols):
        map_info = df_p[[sku_col] + mapping_cols].drop_duplicates(subset=sku_col).set_index(sku_col)
        # 将 map_info 加到 agg
        df_agg = df_agg.join(map_info)
        # 将索引列重命名为 SKU
        display_df = df_agg.reset_index().rename(columns={sku_col: 'SKU'})
    else:
        desc_col = 'Promoted OMSID Description'
        desc_info = df_p[[sku_col, desc_col]].drop_duplicates(subset=sku_col).set_index(sku_col)
        df_agg = df_agg.join(desc_info)
        display_df = df_agg.reset_index().rename(columns={sku_col: 'SKU'})

    # 展示聚合表格
    st.subheader(f"{selected_campaign} 的 SKU 聚合指标表")
    st.dataframe(display_df)
    # 3. 绘制饼图：除 SPA ROAS 外
    st.subheader("SKU 指标占比饼图")
    labels = df_agg.index.tolist()
    base_colors = px.colors.qualitative.Plotly
    color_map = {lbl: base_colors[i % len(base_colors)] for i, lbl in enumerate(labels)}

    # 每行两图布局
    for idx, m in enumerate(metrics):
        if idx % 2 == 0:
            cols = st.columns(2)
        with cols[idx % 2]:
            vals = df_agg[m].values.tolist()
            fig = px.pie(
                names=labels,
                values=vals,
                color=labels,
                color_discrete_map=color_map,
                title=f"{m} 分布",
                hole=0.4  # 设置为环状图

            )
            fig.update_traces(textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

def plot_sku_trends(
    df_promoted: pd.DataFrame,
    sku_col: str = 'Promoted OMSID',
    date_col: str = 'Day'
):
    """
    支持两种 SKU 趋势分析场景：
    1. 对比两个不同 SKU 在同一指标下随时间的趋势；
    2. 对比同一 SKU 在两个不同指标下随时间的趋势，使用共轴双 y 轴折线图。

    使用场景：df_promoted 已过滤到所选 Campaign。
    """
    sku_list = df_promoted[sku_col].unique().tolist()
    mode = st.radio("选择模式", ['跨 SKU 对比同指标', '单 SKU 对比跨指标'], key='sku_trend_mode')

    if mode == '跨 SKU 对比同指标':
        metric = st.selectbox("选择对比指标", ['Clicks','Impressions','SPA Sales','Spend'], key='mode1_metric')
        skus = st.multiselect("选择多个 SKU", sku_list, default=sku_list[:2], key='mode1_skus')
        data = df_promoted[df_promoted[sku_col].isin(skus)]
        fig = px.line(
            data,
            x=date_col,
            y=metric,
            color=sku_col,
            markers=True,
            title=f"SKU 对比：{metric} 趋势"
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        sku = st.selectbox("选择 SKU", sku_list, key='mode2_sku')
        metrics = ['Clicks','Impressions','SPA Sales','Spend']
        col1, col2 = st.columns(2)
        with col1:
            m1 = st.selectbox("第一个指标", metrics, key='mode2_m1')
        with col2:
            m2 = st.selectbox("第二个指标", [m for m in metrics if m != m1], key='mode2_m2')
        data = df_promoted[df_promoted[sku_col] == sku]

        # 使用双 y 轴折线图
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(x=data[date_col], y=data[m1], mode='lines+markers', name=m1),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(x=data[date_col], y=data[m2], mode='lines+markers', name=m2),
            secondary_y=True
        )
        fig.update_layout(
            title_text=f"SKU {sku} 指标对比趋势（{m1} vs {m2}）"
        )
        fig.update_xaxes(title_text=date_col)
        fig.update_yaxes(title_text=m1, secondary_y=False)
        fig.update_yaxes(title_text=m2, secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(data[['Promoted OMSID', 'Promoted OMSID Description', 'Campaign ID', 'Campaign Name', 'Day', 'Clicks', 'Impressions', 'SPA ROAS', 'SPA Sales', 'Spend']])
