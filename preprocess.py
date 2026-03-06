# preprocess.py
import pandas as pd
import streamlit as st
import numpy as np

@st.cache_data
def campaign(df: pd.DataFrame) -> pd.DataFrame:
    mask = df['Interval'].str.contains(r'\d{4}-\d{2}-\d{2} to \d{4}-\d{2}-\d{2}', na=False, regex=True)
    df['Interval'] = np.where(
        mask, 
        pd.to_datetime(df['Interval'].str.split(' to ').str[1], errors = 'coerce').dt.date,
        pd.to_datetime(df['Interval'], format='%Y-%m-%d', errors='coerce').dt.date
    )
    df["Campaign ID"] = df['Campaign ID'].astype(str)
    df = df[df["Status"] == "running"]
    return df

@st.cache_data
def promoted(df: pd.DataFrame,
             campaign_ids: list[str] | None = None,
             sku_map: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    对 Promoted Sales 表进行预处理并映射 HD SKU Map。
    如果已经存在映射列，则直接返回原 df，避免重复合并。
    """
    # 假设映射后新增的列名为 'Mapped SKU'
    mapped_col = 'OMSID'
    if mapped_col in df.columns:
        return df  # 已经做过映射，直接跳过
    
    df["Day"] = pd.to_datetime(df["Day"]).dt.date
    df["Promoted OMSID"] = df["Promoted OMSID Number"].astype(str)
    df["Campaign ID"] = df["Campaign ID"].astype(str)
    if campaign_ids:
        df = df[df['Campaign ID'].isin(campaign_ids)]
    # 合并 SKU 桥表
    if sku_map is not None:
        # sku_map 列示例: ['OMSID', 'OMS THD SKU', 'MFG Model #', 'Product Name (120)']
        df = df.merge(
            sku_map,
            how='left',
            left_on='Promoted OMSID',
            right_on='OMSID'
        ).copy()

    return df

@st.cache_data
def purchased(df: pd.DataFrame, 
              campaign_ids: list[str] | None = None,):
    df["Day"] = pd.to_datetime(df["Day"]).dt.date
    df["Promoted OMSID"] = df["Promoted OMSID Number"].astype(str)
    df["Campaign ID"] = df["Campaign ID"].astype(str)
    df['Purchased OMSID'] = df['Purchased OMSID Number'].astype(str)
    if campaign_ids:
        df = df[df['Campaign ID'].isin(campaign_ids)]

    return df

@st.cache_data
def hd_sku_map(df: pd.DataFrame) -> pd.DataFrame:
    df['OMSID'] = df['OMSID'].astype(str)
    df['OMS THD SKU'] = df['OMS THD SKU'].astype(str)

    return df

@st.cache_data
def rank(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1) 清理列名
    df.columns = df.columns.str.strip()

    # 2) 删除全空行
    df = df.dropna(how="all")

    # 3) 日期列
    df["scraped_date"] = pd.to_datetime(df["scraped_date"], errors="coerce").dt.date

    # 4) 文本列清理
    text_cols = [
        "label_raw",
        "item_id",
        "brand_name",
        "parent_id",
        "canonical_url",
        "product_label",
        "store_sku_number",
        "model_number"
    ]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df.loc[df[col].isin(["nan", "None", ""]), col] = None

    # 5) 数值列清理
    numeric_cols = [
        "order_global",
        "page_no",
        "pos_in_page",
        "price",
        "original_price",
        "avg_rating",
        "total_reviews",
        "inventory"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 6) is_sponsored 规范化
    if "is_sponsored" in df.columns:
        df["is_sponsored"] = df["is_sponsored"].replace({
            True: 1, False: 0,
            "True": 1, "False": 0,
            "true": 1, "false": 0,
            "TRUE": 1, "FALSE": 0,
            "YES": 1, "Yes": 1, "yes": 1,
            "NO": 0, "No": 0, "no": 0
        })
        df["is_sponsored"] = pd.to_numeric(df["is_sponsored"], errors="coerce").fillna(0).astype(int)

    # 7) 只保留 CARRO
    df = df[df["brand_name"].astype(str).str.upper() == "CARRO"].copy()

    if df.empty:
        return df

    # 8) 定义 group_concat 风格聚合函数
    def concat_pages(series):
        vals = (
            pd.Series(series)
            .dropna()
            .astype(int)
            .sort_values()
            .astype(str)
            .tolist()
        )
        # 去重但保持排序后顺序
        vals = list(dict.fromkeys(vals))
        return ",".join(vals) if vals else None

    # 9) 分 sponsored / organic 聚合 page_no
    sponsored_pages = (
        df[df["is_sponsored"] == 1]
        .groupby("item_id")["page_no"]
        .apply(concat_pages)
        .rename("page_no_sponsored")
        .reset_index()
    )

    organic_pages = (
        df[df["is_sponsored"] == 0]
        .groupby("item_id")["page_no"]
        .apply(concat_pages)
        .rename("page_no_organic")
        .reset_index()
    )

    # 10) 每个 item_id 保留一条基础信息
    # 排序后取每个 item 的第一条，尽量保留靠前排名的信息
    df_base = (
        df.sort_values(
            by=["item_id", "order_global", "page_no", "pos_in_page"],
            ascending=[True, True, True, True]
        )
        .groupby("item_id", as_index=False)
        .first()
    )

    # 11) 合并两类 page_no 分布
    df_flat = (
        df_base
        .merge(sponsored_pages, on="item_id", how="left")
        .merge(organic_pages, on="item_id", how="left")
    )

    # 12) 可选：补充出现次数，方便分析
    item_counts = (
        df.groupby("item_id")
        .size()
        .rename("rank_appear_count")
        .reset_index()
    )

    df_flat = df_flat.merge(item_counts, on="item_id", how="left")

    # 13) 调整列顺序
    preferred_cols = [
        "scraped_date",
        "item_id",
        "brand_name",
        "parent_id",
        "product_label",
        "canonical_url",
        "store_sku_number",
        "model_number",
        "price",
        "original_price",
        "avg_rating",
        "total_reviews",
        "inventory",
        "label_raw",
        "order_global",
        "page_no",
        "pos_in_page",
        "is_sponsored",
        "page_no_sponsored",
        "page_no_organic",
        "rank_appear_count"
    ]

    final_cols = [c for c in preferred_cols if c in df_flat.columns] + [
        c for c in df_flat.columns if c not in preferred_cols
    ]

    df_flat = df_flat[final_cols].copy()

    return df_flat