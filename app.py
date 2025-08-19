import streamlit as st
import pandas as pd

st.set_page_config("Homedepot 广告分析工具", layout="wide")
pg = st.navigation([
    st.Page("modules/upload.py", title = "文件上传页", icon = "📥"),
    st.Page("modules/scraper.py", title = "产品信息爬取页", icon = "ℹ️"),
    st.Page("modules/trends.py", title = "广告趋势分析", icon = "📈")
])
pg.run()

