import plotly.express as px
import streamlit as st
import pandas as pd
import numpy as np

def plot_promoted_sunburst(df_merged: pd.DataFrame):
    df = df_merged.copy()
    # 获取唯一 Promoted OMSID 列表
    unique_promoted = df['Promoted OMSID'].dropna().unique()

    # 创建一个映射字典，方便快速查找 Description
    promoted_desc_map = df.groupby('Promoted OMSID')['Promoted OMSID Description_x'] \
                        .first() \
                        .fillna('No description') \
                        .to_dict()
    
    # Streamlit selectbox
    selected_promoted_sku = st.selectbox(
        "请选择需要查看的Promoted SKU",
        options=unique_promoted,
        format_func=lambda x: f"{x} - {promoted_desc_map.get(x, 'No description')}"
    )

    df_selected = df[df['Promoted OMSID'] == selected_promoted_sku]
    df_selected['Category'] = np.where(df_selected['Purchased OMSID'] == df_selected['Promoted OMSID'], 
                            'Promoted', 'Non-Promoted')

    df_sunburst = df_selected.dropna(subset=['Purchased OMSID'])

    if df_sunburst.empty:
        st.info(f"Promoted OMSID {selected_promoted_sku} 没有销售数据可显示。")
        return
    
    # 汇总数据
    df_sunburst_agg = df_sunburst.groupby(['Category','Purchased OMSID'], as_index=False)['SPA Sales_y'].sum()

    # 再计算占比
    df_sunburst_agg['Sales_pct'] = df_sunburst_agg['SPA Sales_y'] / df_sunburst_agg['SPA Sales_y'].sum() * 100

    # 绘制 Sunburst
    fig = px.sunburst(
        df_sunburst_agg,
        path=['Category','Purchased OMSID'],
        values='SPA Sales_y',
        color='SPA Sales_y',  # 父层颜色也会根据总销售额
        color_continuous_scale='viridis',
        hover_data={'SPA Sales_y':':.2f','Sales_pct':':.2f'},
        title=f"Promoted OMSID {selected_promoted_sku} 的广告销售额分布"
    )

    st.plotly_chart(fig, use_container_width=True, key = 'sunburst')

    if 'HD SKU Map' in st.session_state.get('uploaded_data', {}):
        hd_map = st.session_state['uploaded_data']['HD SKU Map'].copy()
        # 确保两边都是字符串，避免匹配失败
        df_display = df_sunburst_agg.merge(
            hd_map,
            left_on='Purchased OMSID',
            right_on='OMSID',
            how='left',
            suffixes=('', '_HDMap')
                )
    else:
        df_display = df_sunburst_agg.copy()
    st.dataframe(df_display)