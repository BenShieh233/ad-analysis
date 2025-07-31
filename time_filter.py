import pandas as pd
import streamlit as st
from datetime import date

import streamlit as st

def time_filters(df, date_col, key_prefix=""):
    st.sidebar.header("🕒 时间范围筛选")
    min_date = df[date_col].min()
    max_date = df[date_col].max()

    start_key = f"{key_prefix}_start"
    end_key = f"{key_prefix}_end"

    # 只在第一次执行时初始化默认值
    if start_key not in st.session_state:
        st.session_state[start_key] = min_date
    if end_key not in st.session_state:
        st.session_state[end_key] = max_date

    # 调用时不传 value，直接绑定 key
    start = st.sidebar.date_input(
        "开始日期",
        min_value=min_date,
        max_value=max_date,
        key=start_key
    )
    end = st.sidebar.date_input(
        "结束日期",
        min_value=min_date,
        max_value=max_date,
        key=end_key
    )

    # 校验顺序
    if start > end:
        st.warning("⚠️ 结束时间不能早于开始时间，请重新选择")
        return df

    # 过滤并返回
    mask = (df[date_col] >= start) & (df[date_col] <= end)
    return df.loc[mask].copy()

