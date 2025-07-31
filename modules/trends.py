import streamlit as st
from time_filter import time_filters
from config import file_configs
from visuals.campaign_ranking import get_ranked_campaigns, plot_campaign_totals, plot_campaign_trends, plot_metric_pie_charts
from visuals.campaign_fields import plot_dual_metric_trends, plot_campaign_radar_ranks
from visuals.promoted_groupby import plot_promoted_sku_rank, plot_sku_trends

def trend():
    if "uploaded_data" not in st.session_state or not st.session_state.uploaded_data:
        st.warning("尚未上传任何数据，请先在“文件上传页”中完成文件上传。")
        st.stop()
    
    data = st.session_state['uploaded_data']
    campaign = data.get('Campaign Summary')
    if campaign is not None and not campaign.empty:
        campaign_date = file_configs['Campaign Summary']['date_col']

    promoted = data.get('Promoted Sales')
    if promoted is not None and not promoted.empty:
        promoted_date = file_configs['Promoted Sales']['date_col']


    # with tabs[0]:
    #     campaign_tab_selection = st.pills("选择要广告分析的功能", ['整体趋势折线图', '单支广告参数对比图'])
    #     df_campaign = time_filters(campaign, campaign_date, key_prefix="campaign")
        
    # with tabs[1]:
    #     df_promoted = time_filters(promoted, promtoed_date, key_prefix="promoted")
    #     st.dataframe(df_promoted)

    tab_selection  = st.pills("选择要查看的页面", ['广告整体表现', 'SKU具体表现'], default="广告整体表现")
    if tab_selection  == "广告整体表现":
        if campaign is None:
            st.warning("请检查是否已上传 Campaign Summary 文件")
            st.stop()

        df_campaign = time_filters(campaign, campaign_date, key_prefix="campaign")
        name_map = dict(zip(df_campaign['Campaign ID'], df_campaign['Campaign Name']))

        campaign_metrics = ["Click Through Rate (CTR) (sum)", "Clicks (sum)",
                          "Cost Per Click (CPC) (sum)", "Cost Per Thousand Views (CPM) (sum)", "Impressions (sum)", "Return on Ad Spend (ROAS) SPA (sum)",
                          "SPA In-Store Sales (sum)", "SPA Online Sales (sum)", "SPA Sales (sum)", "Spend (sum)"]
        mean_metrics = ['Return on Ad Spend (ROAS) SPA (sum)', 'Click Through Rate (CTR) (sum)', 'Cost Per Click (CPC) (sum)', 'Cost Per Thousand Views (CPM) (sum)']
        campaign_tabs = st.tabs([
            "📈 趋势分析",
            "📊 指标分布图",
            "📚 单支广告表现",
            "📱 广告内SKU表现"
        ])
        with campaign_tabs[0]:
            col1, col2 = st.columns(2)

            # 设置分析指标和筛选排名范围的选项
            with col1:
                aggregation_field = st.selectbox("指标", campaign_metrics)
            with col2:
                # 获取完整排名
                ranked_ids, total = get_ranked_campaigns(df_campaign, aggregation_field, 'Campaign ID', mean_metrics)
                # 双头滑块，用户选 m:n
                m, n = st.slider(f"{aggregation_field}的排名范围", 1, len(ranked_ids), (1, min(5, len(ranked_ids))))
            selected_ids = ranked_ids[m-1:n]  # 注意索引偏移
            plot_campaign_totals(total, 'Campaign ID', selected_ids, name_map=name_map)
            st.write("---")
            plot_campaign_trends(df_campaign,
                                 aggregation_field,
                                 'Interval',
                                 'Campaign ID',
                                 'Ad Type',
                                 selected_ids,
                                 name_map,
                                 )
        with campaign_tabs[1]:
            plot_metric_pie_charts(df_campaign, 
                                   campaign_metrics,
                                   aggregation_field,
                                   "Campaign ID",
                                   name_map
                                   )
        with campaign_tabs[2]:

            # 在 Tab3 页面头部定义 selected_campaign
            st.session_state['tab3_campaign'] = st.selectbox("选择 Campaign ID", df_campaign['Campaign ID'].unique())

            # 功能1
            plot_dual_metric_trends(
                df=df_campaign,
                metrics=campaign_metrics,
                date_col='Interval',
                campaign_col='Campaign ID',
                ad_type_col='Ad Type',
                mean_metrics=mean_metrics
            )

            # 功能3
            plot_campaign_radar_ranks(
                df=df_campaign,
                metrics=campaign_metrics,
                campaign_col='Campaign ID',
                mean_metrics=mean_metrics
            )
        
        with campaign_tabs[3]:
            if promoted is None:
                st.warning("若要使用本功能，请检查是否已上传 Promoted Sales 文件")
                st.stop()
                
            ids = df_campaign['Campaign ID'].unique().tolist()
            # 默认选项：如果之前在 tab3 里选过，就用它；否则用第一个
            default = 0
            if 'tab3_campaign' in st.session_state:
                prev = st.session_state['tab3_campaign']
                if prev in ids:
                    default = ids.index(prev)

            selected_campaign = st.selectbox(
                "选择 Campaign ID",
                options=ids,
                index=default,
                key="tab4_selected_campaign"
            )

            start, end = st.session_state['campaign_start'], st.session_state['campaign_end']
            df_promoted = promoted.loc[(promoted['Day'] >= start) & (promoted['Day'] <= end) & (promoted['Campaign ID'] == selected_campaign)].copy()
            if df_promoted.empty:
                st.warning("Auction Banner 广告未包含 promoted SKU")
                st.stop()

            promoted_metrics = ['Clicks','Impressions','SPA ROAS','SPA Sales','Spend']

            sku_tabs = st.tabs([
                'Promoted SKU 累计指标',
                'Promoted SKU 时间趋势'
            ])

            with sku_tabs[0]:
                plot_promoted_sku_rank(
                    df_promoted,
                    selected_campaign,
                    promoted_metrics
                )
            
            with sku_tabs[1]:
                plot_sku_trends(df_promoted)

    elif tab_selection == "SKU具体表现":
        if promoted is None:
            st.warning("请检查是否已上传 Promoted Sales 文件")
            st.stop()

        df_promoted = time_filters(promoted, promoted_date, key_prefix="promoted")

trend()