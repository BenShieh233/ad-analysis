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
    df["Promoted OMSID"] = df["Promoted OMSID"].astype(str)
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
def hd_sku_map(df: pd.DataFrame) -> pd.DataFrame:
    df['OMSID'] = df['OMSID'].astype(str)
    df['OMS THD SKU'] = df['OMS THD SKU'].astype(str)

    return df