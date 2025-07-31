import streamlit as st
import pandas as pd
from config import file_configs
from utils.validate import validate_dataframe
from preprocess import campaign, promoted, hd_sku_map

PREPROCESS_MAP = {
    "campaign": campaign,
    "promoted": promoted,
    "map": hd_sku_map
}

def upload():
    st.header("📥 上传广告数据文件")
    
    # 如果之前已经有上传的数据，就拿出来；否则初始化一个空 dict
    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = {}

    for name, cfg in file_configs.items():
        uploaded_file = st.file_uploader(
            label=f"上传 {name}",
            type=["xlsx", "xls"],
            key=f"uploader_{name}"
        )
    
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file, skiprows=cfg["skiprows"])
                missing = validate_dataframe(df, cfg["required_cols"])
                if missing:
                    st.error(f"{name} 缺少列：{missing}")
                    continue
                else:
                    # 调用对应的与处理函数
                    fn_key = cfg.get("preprocess_fn")

                    if fn_key == 'promoted':
                        # 如果已上传 Campaign Summary，则提取其 Campaign ID 列做筛选
                        campaign_df = st.session_state.uploaded_data.get('Campaign Summary')
                        campaign_ids = campaign_df['Campaign ID'].tolist() if campaign_df is not None else None
                        sku_map_df = st.session_state.uploaded_data.get('HD SKU Map')
                        df = PREPROCESS_MAP[fn_key](df, campaign_ids, sku_map_df)

                    elif fn_key in PREPROCESS_MAP:
                        df = PREPROCESS_MAP[fn_key](df)

                    st.success(f"{name} 上传并预处理完成，共 {len(df)} 行")
                    st.session_state.uploaded_data[name] = df

            except Exception as e:
                st.error(f"读取“{name}”时出错，请检查格式 {e}")

    st.markdown("---")
    st.subheader("🗄️ 已上传并持久化的数据")
    if st.session_state.uploaded_data:
        for name, df in st.session_state.uploaded_data.items():
            st.write(f"**{name}**：{len(df)} 行")
            st.dataframe(df.head())
            st.write("-----")
    else:
        st.info("尚未上传任何通过校验的文件。")
    # 上传流程结束后，全局处理依赖关系
    # 自动将 HD SKU Map 应用到 Promoted Sales
    if "HD SKU Map" in st.session_state.uploaded_data and 'Promoted Sales' in st.session_state.uploaded_data:
        prom_df = st.session_state.uploaded_data['Promoted Sales']
        camp_df = st.session_state.uploaded_data.get('Campaign Summary')
        camp_ids = camp_df['Campaign ID'].tolist() if camp_df is not None else None
        sku_map_df = st.session_state.uploaded_data["HD SKU Map"]
        # 重新调用预处理以合并映射
        merged = promoted(prom_df, camp_ids, sku_map_df)
        st.session_state.uploaded_data['Promoted Sales'] = merged
        st.success("已自动将 SKU Map 应用到 Promoted Sales")
        
upload()
