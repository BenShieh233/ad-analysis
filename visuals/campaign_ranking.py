import streamlit as st
import plotly.express as px
import pandas as pd

def get_ranked_campaigns(
    df: pd.DataFrame,
    metric: str,
    campaign_col: str,
    mean_metrics: list[str]
) -> tuple[list[str], pd.Series]:
    """
    根据指标对所有 Campaign 进行汇总排名，返回按降序排列的 Campaign ID 列表和对应总量序列。
    """
    if metric in mean_metrics:
        total = df.groupby(campaign_col)[metric].mean().sort_values(ascending=False)
    else:    
        total = df.groupby(campaign_col)[metric].sum().sort_values(ascending=False)
    ranked_ids = total.index.tolist()
    return ranked_ids, total


def plot_campaign_totals(
    total: pd.Series,
    campaign_col: str,
    selected_ids: list[str] | None = None,
    name_map: dict[str, str] | None = None,
    name_max_len: int = 20
):
    """
    绘制 Campaign 总量的柱状图，按总量降序排列。
    如果提供了 selected_ids，则仅展示这些 IDs。

    可以通过 name_map 提供 Campaign ID 到 Name 的映射，
    并在标签中展示省略后的 Name。
    """
    # 判断展示范围
    if selected_ids:
        series = total.loc[selected_ids]
        title = "选定 Campaign 总量排名"
        order = selected_ids
    else:
        series = total
        title = "所有 Campaign 总量排名"
        order = total.index.tolist()

    # 构建标签
    labels = []
    for cid in order:
        if name_map and cid in name_map:
            name = name_map[cid]
            labels.append((cid, name))
        else:
            labels.append((cid, None))

    # 生成最终显示标签
    display_labels = []
    for cid, name in labels:
        if name:
            label = name if len(name) <= name_max_len else name[:name_max_len] + '...'
            display_labels.append(f"{cid} - {label}")
        else:
            display_labels.append(cid)

    df_totals = pd.DataFrame({"_id": order, "label": display_labels, '总量': series.values})
    df_totals["text_总量"] = df_totals["总量"].apply(lambda x: f"{x:.2f}")

    # 颜色映射
    color_map = px.colors.qualitative.Plotly
    color_discrete_map = {disp: color_map[i % len(color_map)] for i, disp in enumerate(display_labels)}

    fig = px.bar(
        df_totals,
        x='label',
        y='总量',
        text = "text_总量",
        color='label',
        category_orders={'label': display_labels},
        color_discrete_map=color_discrete_map,
        labels={"label": campaign_col, "总量": "总量"},
        title=title
    )
    fig.update_layout(
        xaxis_title=campaign_col,
        yaxis_title='总量',
        template='plotly_white',
        showlegend=False
    )
    # 正确调用 plotly_chart
    st.plotly_chart(fig, use_container_width=True)

def plot_campaign_trends(
    df: pd.DataFrame,
    metric: str,
    date_col: str,
    campaign_col: str,
    ad_type_col: str,
    selected_ids: list[str],
    name_map: dict[str, str] | None = None,
    name_max_len: int = 20
):
    """
    绘制选定 Campaign 的折线趋势图，保证与柱状图一致的顺序和配色。
    支持在图例中显示 Campaign Name，并截断过长名称。

    参数:
    - df: 原始包含时间与指标的 DataFrame
    - metric: 用于趋势的指标列名
    - date_col: 时间列名
    - campaign_col: Campaign ID 列名
    - ad_type_col: 广告类型列名，用于 dash 样式
    - selected_ids: 要展示的 Campaign ID 列表，顺序即图例顺序
    - name_map: 可选的 Campaign ID -> Name 映射，用于图例标签
    - name_max_len: 图例标签中最大名称长度
    """
    # 过滤数据
    filtered = df[df[campaign_col].isin(selected_ids)].copy()

    # 构建图例标签
    def make_label(cid):
        if name_map and cid in name_map:
            nm = name_map[cid]
            short = nm if len(nm) <= name_max_len else nm[:name_max_len] + '...'
            return f"{cid} - {short}"
        return cid

    filtered['label'] = filtered[campaign_col].apply(make_label)
    legend_order = [make_label(cid) for cid in selected_ids]

    # 颜色映射
    colors = px.colors.qualitative.Plotly
    color_discrete_map = {lbl: colors[i % len(colors)] for i, lbl in enumerate(legend_order)}

    # 绘制折线图
    fig = px.line(
        filtered,
        x=date_col,
        y=metric,
        color='label',
        line_dash=ad_type_col,
        markers=True,
        title=f"{metric} 趋势 (选定 Campaign)",
        category_orders={'label': legend_order},
        color_discrete_map=color_discrete_map
    )
    # dash 样式
    dash_map = {'PLA': 'solid', 'AUCTION_BANNER': 'dash'}
    for trace in fig.data:
        parts = trace.name.split(', ')
        ad = parts[1] if len(parts) > 1 else None
        trace.line.dash = dash_map.get(ad, 'solid')

    fig.update_layout(
        xaxis_title=date_col,
        yaxis_title=metric,
        template='plotly_white',
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(filtered)

def plot_metric_pie_charts(
    df: pd.DataFrame,
    metrics: list[str],
    aggregation_field: str,
    campaign_col: str,
    name_map: dict[str, str] | None = None,
    name_max_len: int = 20
):
    mean_metrics = [
        'Return on Ad Spend (ROAS) SPA (sum)',
        'Click Through Rate (CTR) (sum)',
        'Cost Per Click (CPC) (sum)',
        'Cost Per Thousand Views (CPM) (sum)'
    ]

    total_main = df.groupby(campaign_col)[aggregation_field].sum().sort_values(ascending=False)
    ranked = total_main.index.tolist()
    max_n = len(ranked)

    top_n = st.slider(f"选择 Top N (按 {aggregation_field} 排序)", 1, max_n, min(5, max_n))
    include_others = st.checkbox("包含 Others", value=True)
    top_ids = ranked[:top_n]
    other_ids = ranked[top_n:]

    # label 构建
    def build_label(cid):
        if name_map and cid in name_map:
            nm = name_map[cid]
            short = nm if len(nm) <= name_max_len else nm[:name_max_len] + '...'
            return f"{cid} - {short}"
        return cid

    label_map = {cid: build_label(cid) for cid in top_ids}
    if include_others:
        label_map["Others"] = "Others"

    labels_ordered = [label_map[cid] for cid in top_ids]
    if include_others:
        labels_ordered.append("Others")

    # 颜色映射
    colors = px.colors.qualitative.Plotly
    color_map = {label: colors[i % len(colors)] for i, label in enumerate(labels_ordered)}

    # 主图
    if aggregation_field in mean_metrics:
        main_vals = df.groupby(campaign_col)[aggregation_field].mean()
        data = [main_vals.loc[cid] for cid in top_ids]
        if include_others:
            others_val = main_vals.loc[other_ids].mean()
            data.append(others_val)
        df_main = pd.DataFrame({'label': labels_ordered, 'value': data})
        fig_main = px.bar(
            df_main,
            x='label',
            y='value',
            text='value',
            color='label',
            color_discrete_map=color_map,
            category_orders={'label': labels_ordered},
            title=f"{aggregation_field} 平均值 (Top {top_n}{' + Others' if include_others else ''})"
        )
        fig_main.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    else:
        values_main = [total_main[cid] for cid in top_ids]
        if include_others:
            others_total = total_main.loc[other_ids].sum()
            values_main.append(others_total)
        fig_main = px.pie(
            names=labels_ordered,
            values=values_main,
            color=labels_ordered,
            color_discrete_map=color_map,
            title=f"{aggregation_field} 分布 (Top {top_n}{' + Others' if include_others else ''})",
            hole=0.4  # 设置为环状图

        )
        fig_main.update_traces(textinfo='percent+label')

    st.subheader("指标分布对比")
    other_metrics = [m for m in metrics if m != aggregation_field]
    cols = st.columns(2)
    with cols[0]:
        st.plotly_chart(fig_main, use_container_width=True)

    # 第一个对比指标
    m0 = other_metrics[0]
    with cols[1]:
        title0 = f"{m0} 分布 (Top {top_n}{' + Others' if include_others else ''})"
        if m0 in mean_metrics:
            mean_vals = df.groupby(campaign_col)[m0].mean()
            values = [mean_vals.loc[cid] for cid in top_ids]
            if include_others:
                others_val = mean_vals.loc[other_ids].mean()
                values.append(others_val)
            df0 = pd.DataFrame({'label': labels_ordered, 'value': values})
            fig0 = px.bar(
                df0,
                x='label',
                y='value',
                text='value',
                color='label',
                color_discrete_map=color_map,
                category_orders={'label': labels_ordered},
                title=title0
            )
            fig0.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        else:
            sum_vals = df.groupby(campaign_col)[m0].sum()
            values = [sum_vals.loc[cid] for cid in top_ids]
            if include_others:
                values.append(sum_vals.loc[other_ids].sum())
            fig0 = px.pie(
                names=labels_ordered,
                values=values,
                color=labels_ordered,
                color_discrete_map=color_map,
                title=title0,
                hole=0.4  # 设置为环状图

            )
            fig0.update_traces(textinfo='percent+label')
        st.plotly_chart(fig0, use_container_width=True)

    # 其余指标
    for idx, m in enumerate(other_metrics[1:], start=1):
        if idx % 2 == 1:
            cols = st.columns(2)
        with cols[idx % 2]:
            titlem = f"{m} 分布 (Top {top_n}{' + Others' if include_others else ''})"
            if m in mean_metrics:
                mean_vals = df.groupby(campaign_col)[m].mean()
                values = [mean_vals.loc[cid] for cid in top_ids]
                if include_others:
                    values.append(mean_vals.loc[other_ids].mean())
                dfm = pd.DataFrame({'label': labels_ordered, 'value': values})
                figm = px.bar(
                    dfm,
                    x='label',
                    y='value',
                    text='value',
                    color='label',
                    color_discrete_map=color_map,
                    category_orders={'label': labels_ordered},
                    title=titlem
                )
                figm.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            else:
                sum_vals = df.groupby(campaign_col)[m].sum()
                values = [sum_vals.loc[cid] for cid in top_ids]
                if include_others:
                    values.append(sum_vals.loc[other_ids].sum())
                figm = px.pie(
                    names=labels_ordered,
                    values=values,
                    color=labels_ordered,
                    color_discrete_map=color_map,
                    title=titlem,
                    hole=0.4  # 设置为环状图

                )
                figm.update_traces(textinfo='percent+label')
            st.plotly_chart(figm, use_container_width=True)

# def plot_metric_pie_charts(
#     df: pd.DataFrame,
#     metrics: list[str],
#     aggregation_field: str,
#     campaign_col: str,
#     name_map: dict[str, str] | None = None,
#     name_max_len: int = 20
# ):
#     """
#     1. 根据 aggregation_field 总量排名，选前 N，并可选将其他归为 "Others"；
#     2. 绘制 aggregation_field 的饼图或条形图；
#     3. 对其它指标按相同 top_ids (含 Others 可选) 绘制饼图或条形图；
#     4. 布局：主图与第一个其他指标同一行，其余两图一行。
#     """
#     # 聚合主指标
#     total_main = df.groupby(campaign_col)[aggregation_field].sum().sort_values(ascending=False)
#     ranked = total_main.index.tolist()

#     # 选择 Top N 与 Others 开关
#     max_n = len(ranked)
#     top_n = st.slider(f"选择 Top N (按 {aggregation_field} 排序)", 1, max_n, min(5, max_n))
#     include_others = st.checkbox("包含 Others", value=True)
#     top_ids = ranked[:top_n]
#     other_main = total_main.iloc[top_n:].sum()

#     # 构建标签与数值
#     labels_main, values_main = [], []
#     for cid in top_ids:
#         lbl = cid
#         if name_map and cid in name_map:
#             nm = name_map[cid]
#             short = nm if len(nm) <= name_max_len else nm[:name_max_len] + '...'
#             lbl = f"{cid} - {short}"
#         labels_main.append(lbl)
#         values_main.append(total_main[cid])
#     if include_others and other_main > 0:
#         labels_main.append('Others')
#         values_main.append(other_main)


#     # 颜色映射
#     colors = px.colors.qualitative.Plotly
#     color_map = {lbl: colors[i % len(colors)] for i, lbl in enumerate(labels_main)}

#     # 绘制主图
#     mean_metrics = [
#         'Return on Ad Spend (ROAS) SPA (sum)',
#         'Click Through Rate (CTR) (sum)',
#         'Cost Per Click (CPC) (sum)',
#         'Cost Per Thousand Views (CPM) (sum)'
#     ]
#     if aggregation_field in mean_metrics:
#         main_vals = df.groupby(campaign_col)[aggregation_field].mean().reindex(top_ids)
#         df_main = pd.DataFrame({'label': labels_main[:len(top_ids)], 'value': main_vals.values})
#         if include_others:
#             df_main = pd.concat([df_main, pd.DataFrame([{'label': 'Others', 'value': df.groupby(campaign_col)[aggregation_field].mean().iloc[top_n:].mean()}])], ignore_index=True)  # noqa: E501{'label': 'Others', 'value': df.groupby(campaign_col)[aggregation_field].mean().iloc[top_n:].mean()}, ignore_index=True)
#         fig_main = px.bar(
#             df_main,
#             x='label',
#             y='value',
#             text='value',
#             color='label',
#             color_discrete_map=color_map,
#             category_orders={'label': labels_main},
#             labels={'value': aggregation_field},
#             title=f"{aggregation_field} 平均值 (Top {top_n}{' + Others' if include_others else ''})"
#         )
#         fig_main.update_traces(texttemplate='%{text:.2f}', textposition='outside')
#     else:
#         fig_main = px.pie(
#             names=labels_main,
#             values=values_main,
#             color=labels_main,
#             color_discrete_map=color_map,
#             title=f"{aggregation_field} 分布 (Top {top_n}{' + Others' if include_others else ''})"
#         )
#         fig_main.update_traces(textinfo='percent+label')

#     # 布局
#     st.subheader("指标分布对比")
#     other_metrics = [m for m in metrics if m != aggregation_field]
#     cols = st.columns(2)
#     with cols[0]:
#         st.plotly_chart(fig_main, use_container_width=True)

#     # 绘制第一个其他指标
#     m0 = other_metrics[0]
#     with cols[1]:
#         title0 = f"{m0} 分布 (Top {top_n}{' + Others' if include_others else ''})"
#         if m0 in mean_metrics:
#             vals0 = df.groupby(campaign_col)[m0].mean().reindex(top_ids)
#             df0 = pd.DataFrame({'label': labels_main[:len(top_ids)], 'value': vals0.values})
#             if include_others:
#                 df0 = pd.concat([df0, pd.DataFrame([{'label': 'Others', 'value': df.groupby(campaign_col)[m0].mean().iloc[top_n:].mean()}])], ignore_index=True)  # noqa: E501{'label': 'Others', 'value': df.groupby(campaign_col)[m0].mean().iloc[top_n:].mean()}, ignore_index=True)
#             fig0 = px.bar(
#                 df0,
#                 x='label',
#                 y='value',
#                 text='value',
#                 color='label',
#                 color_discrete_map=color_map,
#                 category_orders={'label': labels_main},
#                 labels={'value': m0},
#                 title=title0
#             )
#             fig0.update_traces(texttemplate='%{text:.2f}', textposition='outside')
#         else:
#             tot0 = df.groupby(campaign_col)[m0].sum().reindex(top_ids)
#             vals0 = tot0.values.tolist()
#             if include_others:
#                 vals0.append(df.groupby(campaign_col)[m0].sum().iloc[top_n:].sum())
#             fig0 = px.pie(
#                 names=labels_main,
#                 values=vals0,
#                 color=labels_main,
#                 color_discrete_map=color_map,
#                 title=title0
#             )
#             fig0.update_traces(textinfo='percent+label')
#         st.plotly_chart(fig0, use_container_width=True)

#     # 其余指标两两排列
#     for idx, m in enumerate(other_metrics[1:], start=1):
#         if idx % 2 == 1:
#             cols = st.columns(2)
#         with cols[idx % 2]:
#             titlem = f"{m} 分布 (Top {top_n}{' + Others' if include_others else ''})"
#             if m in mean_metrics:
#                 vals = df.groupby(campaign_col)[m].mean().reindex(top_ids).values.tolist()
#                 dfm = pd.DataFrame({'label': labels_main[:len(top_ids)], 'value': vals})
#                 if include_others:
#                     dfm = pd.concat([dfm, pd.DataFrame([{'label': 'Others', 'value': df.groupby(campaign_col)[m].mean().iloc[top_n:].mean()}])], ignore_index=True)  # noqa: E501{'label': 'Others', 'value': df.groupby(campaign_col)[m].mean().iloc[top_n:].mean()}, ignore_index=True)
#                 figm = px.bar(
#                     dfm,
#                     x='label',
#                     y='value',
#                     text='value',
#                     color='label',
#                     color_discrete_map=color_map,
#                     category_orders={'label': labels_main},
#                     labels={'value': m},
#                     title=titlem
#                 )
#                 figm.update_traces(texttemplate='%{text:.2f}', textposition='outside')
#             else:
#                 # 总结所有 campaign 的该指标值
#                 metric_sum = df.groupby(campaign_col)[m].sum()

#                 # 根据 aggregation_field 事先定义好的 top_ids 来划分
#                 main_values = metric_sum.loc[metric_sum.index.isin(top_ids)]
#                 others_value = metric_sum.loc[~metric_sum.index.isin(top_ids)].sum()

#                 tot = main_values.tolist()
#                 labels_main = main_values.index.tolist()

#                 if include_others and others_value > 0:
#                     tot.append(others_value)
#                     labels_main.append("Others")

#                 figm = px.pie(
#                     names=labels_main,
#                     values=tot,
#                     color=labels_main,
#                     color_discrete_map=color_map,
#                     title=titlem
#                 )
#                 figm.update_traces(textinfo='percent+label')
#             st.plotly_chart(figm, use_container_width=True)

# def plot_metric_pie_charts(
#     df: pd.DataFrame,
#     metrics: list[str],
#     aggregation_field: str,
#     campaign_col: str,
#     name_map: dict[str, str] | None = None,
#     name_max_len: int = 20
# ):
#     """
#     1. 根据 aggregation_field 总量排名，选前 N，并将其他归为 "Others"；
#     2. 绘制 aggregation_field 的百分比饼图；
#     3. 绘制其他指标的百分比饼图或条形图，确保使用各自聚合值；
#     4. 布局：主饼图与第一个其他指标图同一行，其他图两两分行。
#     """
#     # 聚合 aggregation_field 总量并排序
#     total_main = df.groupby(campaign_col)[aggregation_field].sum().sort_values(ascending=False)
#     ranked = total_main.index.tolist()

#     # 用户选择 Top N
#     max_n = len(ranked)
#     top_n = st.slider(f"选择 Top N (按 {aggregation_field} 排序)", 1, max_n, min(5, max_n))
#     top_ids = ranked[:top_n]
#     other_value = total_main.iloc[top_n:].sum()

#     # 构建主饼图数据
#     labels_main = []
#     values_main = []
#     for cid in top_ids:
#         label = cid
#         if name_map and cid in name_map:
#             nm = name_map[cid]
#             short = nm if len(nm) <= name_max_len else nm[:name_max_len] + '...'
#             label = f"{cid} - {short}"
#         labels_main.append(label)
#         values_main.append(total_main[cid])
#     if other_value > 0:
#         labels_main.append('Others')
#         values_main.append(other_value)

#     # 配色映射
#     base_colors = px.colors.qualitative.Plotly
#     color_map = {lbl: base_colors[i % len(base_colors)] for i, lbl in enumerate(labels_main)}

#     # 主图
#     mean_metrics = ['Return on Ad Spend (ROAS) SPA (sum)', 'Click Through Rate (CTR) (sum)', 'Cost Per Click (CPC) (sum)', 'Cost Per Thousand Views (CPM) (sum)']
#     if aggregation_field in mean_metrics:
#         # 对于平均值类指标使用条形图
#         agg_vals_main = df.groupby(campaign_col)[aggregation_field].mean().loc[top_ids]
#         df_main = pd.DataFrame({'label': labels_main[:len(top_ids)], 'value': agg_vals_main.values})
#         fig_main = px.bar(
#             df_main,
#             x='label',
#             y='value',
#             text='value',
#             color='label',
#             color_discrete_map=color_map,
#             category_orders={'label': labels_main[:len(top_ids)]},
#             labels={'value': aggregation_field},
#             title=f"{aggregation_field} 平均值 (Top {top_n})"
#         )
#         fig_main.update_traces(texttemplate='%{text:.2f}', textposition='outside')
#     else:
#         # 普通饼图
#         fig_main = px.pie(
#             names=labels_main,
#             values=values_main,
#             color=labels_main,
#             color_discrete_map=color_map,
#             title=f"{aggregation_field} 分布 (Top {top_n} + Others)"
#         )
#         fig_main.update_traces(textinfo='percent+label')(textinfo='percent+label')

#     # 布局初始化
#     st.subheader("指标分布对比")
#     other_metrics = [m for m in metrics if m != aggregation_field]
#     cols = st.columns(2)

#     # 第一行：主饼图和第一个其他指标
#     with cols[0]:
#         st.plotly_chart(fig_main, use_container_width=True)

#     m0 = other_metrics[0]
#     with cols[1]:
#         if m0 in ['Return on Ad Spend (ROAS) SPA (sum)', 'Click Through Rate (CTR) (sum)', 'Cost Per Click (CPC) (sum)', 'Cost Per Thousand Views (CPM) (sum)']:
#             # 平均值条形图
#             agg_vals = df.groupby(campaign_col)[m0].mean().loc[top_ids]
#             labels = labels_main[:len(top_ids)]
#             df_bar = pd.DataFrame({'label': labels, 'value': agg_vals.values})
#             fig0 = px.bar(
#                 df_bar,
#                 x='label',
#                 y='value',
#                 color='label',
#                 color_discrete_map=color_map,
#                 category_orders={'label': labels},
#                 title=m0
#             )
#             fig0.update_traces(texttemplate='%{y:.2f}', textposition='outside')
#             st.plotly_chart(fig0, use_container_width=True)
#         else:
#             # 其它指标总量饼图
#             agg_vals = df.groupby(campaign_col)[m0].sum().loc[top_ids]
#             values = [agg_vals[c] for c in top_ids]
#             fig0 = px.pie(
#                 names=labels_main[:len(top_ids)],
#                 values=values,
#                 color=labels_main[:len(top_ids)],
#                 color_discrete_map=color_map,
#                 title=m0
#             )
#             fig0.update_traces(textinfo='percent+label')
#             st.plotly_chart(fig0, use_container_width=True)

#     # 后续指标两两排列
#     for idx, m in enumerate(other_metrics[1:], start=1):
#         if idx % 2 == 1:
#             cols = st.columns(2)
#         with cols[idx % 2]:
#             if m in ['Return on Ad Spend (ROAS) SPA (sum)', 'Click Through Rate (CTR) (sum)', 'Cost Per Click (CPC) (sum)', 'Cost Per Thousand Views (CPM) (sum)']:
#                 agg_vals = df.groupby(campaign_col)[m].mean().loc[top_ids]
#                 df_bar = pd.DataFrame({'label': labels_main[:len(top_ids)], 'value': agg_vals.values})
#                 fig_bar = px.bar(
#                     df_bar,
#                     x='label',
#                     y='value',
#                     color='label',
#                     color_discrete_map=color_map,
#                     category_orders={'label': labels_main[:len(top_ids)]},
#                     title=m
#                 )
#                 fig_bar.update_traces(texttemplate='%{y:.2f}', textposition='outside')
#                 st.plotly_chart(fig_bar, use_container_width=True)
#             else:
#                 agg_vals = df.groupby(campaign_col)[m].sum().loc[top_ids]
#                 values = [agg_vals[c] for c in top_ids]
#                 fig_p = px.pie(
#                     names=labels_main[:len(top_ids)],
#                     values=values,
#                     color=labels_main[:len(top_ids)],
#                     color_discrete_map=color_map,
#                     title=m
#                 )
#                 fig_p.update_traces(textinfo='percent+label')
#                 st.plotly_chart(fig_p, use_container_width=True)
