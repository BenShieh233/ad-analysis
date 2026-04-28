import os
import streamlit as st
import pandas as pd
from config import file_configs
from utils.validate import validate_dataframe
from preprocess import campaign, promoted, purchased, hd_sku_map, rank

PREPROCESS_MAP = {
    "campaign": campaign,
    "promoted": promoted,
    "purchased": purchased,
    "map": hd_sku_map,
    "rank": rank
}

PERSIST_DIR = "persist_data"
PERSIST_FILE = os.path.join(PERSIST_DIR, "uploaded_data.pkl")


def clear_persisted_data():
    try:
        if os.path.exists(PERSIST_FILE):
            os.remove(PERSIST_FILE)
    except Exception as e:
        st.error(f"清空持久化数据失败：{e}")


def upload():
    st.header("📥 上传广告数据文件")

    # 仅使用当前 Streamlit session，避免上一个使用者的数据被下一个使用者看到。
    if "uploaded_data" not in st.session_state:
        st.session_state.uploaded_data = {}

    if "upload_reset_token" not in st.session_state:
        st.session_state.upload_reset_token = 0

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🗑️ 清空当前会话数据"):
            st.session_state.uploaded_data = {}
            st.session_state.pop("product_results", None)
            st.session_state.upload_reset_token += 1
            clear_persisted_data()
            st.success("已清空当前会话数据")
            st.rerun()
    with col2:
        st.caption("上传数据只保存在当前会话；不会自动读取或写入本地持久化文件。")

    for name, cfg in file_configs.items():
        uploaded_file = st.file_uploader(
            label=f"上传 {name}",
            type=["xlsx", "xls"],
            key=f"uploader_{name}_{st.session_state.upload_reset_token}"
        )

        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file, skiprows=cfg.get("skiprows", 0))

                required_cols = cfg.get("required_cols", [])
                missing = validate_dataframe(df, required_cols) if required_cols else []

                if missing:
                    st.error(f"{name} 缺少列：{missing}")
                    continue

                fn_key = cfg.get("preprocess_fn")

                if fn_key == "promoted":
                    campaign_df = st.session_state.uploaded_data.get("Campaign Summary")
                    campaign_ids = campaign_df["Campaign ID"].tolist() if campaign_df is not None else None
                    sku_map_df = st.session_state.uploaded_data.get("HD SKU Map")
                    df = PREPROCESS_MAP[fn_key](df, campaign_ids, sku_map_df)

                elif fn_key == "purchased":
                    campaign_df = st.session_state.uploaded_data.get("Campaign Summary")
                    campaign_ids = campaign_df["Campaign ID"].tolist() if campaign_df is not None else None
                    df = PREPROCESS_MAP[fn_key](df, campaign_ids)

                elif fn_key in PREPROCESS_MAP:
                    df = PREPROCESS_MAP[fn_key](df)

                st.success(f"{name} 上传并预处理完成，共 {len(df)} 行")

                st.session_state.uploaded_data[name] = df

            except Exception as e:
                st.error(f"读取“{name}”时出错，请检查格式：{e}")

    st.markdown("---")
    st.subheader("🗄️ 已上传的数据（当前会话）")

    if st.session_state.uploaded_data:
        for name, df in st.session_state.uploaded_data.items():
            st.write(f"**{name}**：{len(df)} 行")
            st.dataframe(df)
            st.write("-----")
    else:
        st.info("尚未上传任何通过校验的文件。")

    # 1) 自动将 HD SKU Map 应用到 Promoted Sales
    if (
        "uploaded_data" in st.session_state
        and st.session_state.uploaded_data is not None
        and "HD SKU Map" in st.session_state.uploaded_data
        and "Promoted Sales" in st.session_state.uploaded_data
    ):
        prom_df = st.session_state.uploaded_data["Promoted Sales"]
        camp_df = st.session_state.uploaded_data.get("Campaign Summary")
        camp_ids = camp_df["Campaign ID"].tolist() if camp_df is not None else None
        sku_map_df = st.session_state.uploaded_data["HD SKU Map"]

        merged = promoted(prom_df, camp_ids, sku_map_df)

        st.session_state.uploaded_data["Promoted Sales"] = merged

        st.success("已自动将 SKU Map 应用到 Promoted Sales")

    # 2) 将爬取结果合并到 Promoted Sales
    if (
        "product_results" in st.session_state
        and st.session_state.uploaded_data is not None
        and "Promoted Sales" in st.session_state.uploaded_data
    ):
        product_df = st.session_state.get("product_results")

        if isinstance(product_df, pd.DataFrame) and not product_df.empty:
            prom_df = st.session_state.uploaded_data["Promoted Sales"].copy()

            # 建立映射：(campaign_id, sku) -> status
            product_df["campaign_id"] = product_df["campaign_id"].astype(str)
            product_df["sku"] = product_df["sku"].astype(str)

            keys = list(zip(product_df["campaign_id"], product_df["sku"]))
            values = product_df["status"]
            sku_campaign_to_status = dict(zip(keys, values))

            prom_df["Campaign ID"] = prom_df["Campaign ID"].astype(str)
            prom_df["Promoted OMSID Number"] = prom_df["Promoted OMSID Number"].astype(str)

            prom_df["Status"] = prom_df.apply(
                lambda row: sku_campaign_to_status.get(
                    (row["Campaign ID"], row["Promoted OMSID Number"]),
                    "Not Found"
                ),
                axis=1
            )

            st.session_state.uploaded_data["Promoted Sales"] = prom_df

            st.success("已自动将 active状态 应用到 Promoted Sales")

    # 3) 如果存在扁平化后的 Daily Rank，则将 page_no_sponsored / page_no_organic 合并到 Promoted Sales
    if (
        "uploaded_data" in st.session_state
        and st.session_state.uploaded_data is not None
        and "Promoted Sales" in st.session_state.uploaded_data
        and "Daily Rank" in st.session_state.uploaded_data
    ):
        prom_df = st.session_state.uploaded_data["Promoted Sales"].copy()
        rank_df = st.session_state.uploaded_data["Daily Rank"].copy()

        if not prom_df.empty and not rank_df.empty:
            # 统一键类型
            if "Promoted OMSID" in prom_df.columns:
                prom_df["Promoted OMSID"] = prom_df["Promoted OMSID"].astype(str)
                left_key = "Promoted OMSID"
            else:
                prom_df["Promoted OMSID Number"] = prom_df["Promoted OMSID Number"].astype(str)
                left_key = "Promoted OMSID Number"

            rank_df["item_id"] = rank_df["item_id"].astype(str)

            # 只取需要带入的列
            rank_merge_cols = ["item_id", "page_no_sponsored", "page_no_organic"]
            rank_merge_df = rank_df[rank_merge_cols].drop_duplicates(subset=["item_id"]).copy()

            # 先删旧列，避免重复 merge 产生 _x / _y
            for col in ["page_no_sponsored", "page_no_organic"]:
                if col in prom_df.columns:
                    prom_df = prom_df.drop(columns=[col])

            prom_df = prom_df.merge(
                rank_merge_df,
                how="left",
                left_on=left_key,
                right_on="item_id"
            )

            # item_id 只是辅助 merge 用，Promoted Sales 里不一定需要保留
            prom_df = prom_df.drop(columns=["item_id"], errors="ignore")

            st.session_state.uploaded_data["Promoted Sales"] = prom_df

            st.success("已自动将 Daily Rank 的 page_no_sponsored / page_no_organic 合并到 Promoted Sales")

    # 最后展示更新后的 Promoted Sales
    if (
        "uploaded_data" in st.session_state
        and st.session_state.uploaded_data is not None
        and "Promoted Sales" in st.session_state.uploaded_data
    ):
        st.markdown("---")
        st.subheader("📌 当前 Promoted Sales（更新后）")
        st.dataframe(st.session_state.uploaded_data["Promoted Sales"])


upload()
