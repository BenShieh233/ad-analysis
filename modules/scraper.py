import requests
import pandas as pd
import json
import time
import streamlit as st
# 提取单个产品的函数

headers = {
    "accept": "application/json",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "active-user-role": "offsite_self_serve",
    "baggage": "sentry-environment=production,sentry-public_key=cf4f0f8b8d8c4363b447c22ad88f1f88,sentry-trace_id=6daee48c51a141aabf1b17440855741d,sentry-replay_id=f5d1414bcb2845649d29456e13136fb8,sentry-transaction=%2Fr%2F%3AstoreId%2Fcampaign%2Fdetails%2F%3AcampaignId,sentry-sampled=true,sentry-sample_rand=0.4349195206881652,sentry-sample_rate=1",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "cookie": "__stripe_mid=6eff1869-934d-445a-9deb-fedc84931d84c1b632; ajs_anonymous_id=b73b63d3-ed7d-44ef-b819-66177f184ec6; ajs_user_id=34217; ajs_group_id=33602; _hjSessionUser_3929290=eyJpZCI6ImZjYjkxMjgyLTM0YzgtNWUzYS1hMzljLWJhZjljNjYxMGU2NSIsImNyZWF0ZWQiOjE3NTMxMjg0Mzc4NDYsImV4aXN0aW5nIjp0cnVlfQ==; _cioid=34217; _ga=GA1.2.324959639.1755098067; ajs_user_id=34217; ajs_anonymous_id=b73b63d3-ed7d-44ef-b819-66177f184ec6; gatewayaffinityCORS=eb6c397b2dd93891a62fc56a22511c9b; gatewayaffinity=eb6c397b2dd93891a62fc56a22511c9b; csrftoken=HSJNRliEHMp3QLnYtWVkQfe9YCBchhazl9bh1UShBhO9SdzxRyDP8No1RbVEMFDD; sessionid=1l91x1vwm2xyq44wrm5wnsurh55y6nyf; _hjSession_3929290=eyJpZCI6IjY0ZjJmZmE3LWFiODItNDBmYy1hMmQ4LTcwM2M0NGNmM2RiZiIsImMiOjE3NzI4MTc3NjMwMzQsInMiOjEsInIiOjEsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=; _hjHasCachedUserAttributes=true; _hjUserAttributesHash=147bbddd533807c7cc574acc4779e548; _dd_s=logs=1&id=bfc0ba76-2587-4950-802c-25c6d46caa6f&created=1772817763688&expire=1772820096523",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://us.orangeapronmedia.com/r/33602/campaign/details/122403",
    "sec-ch-ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "sentry-trace": "6daee48c51a141aabf1b17440855741d-8e079938f667ac6c-1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "x-csrftoken": "HSJNRliEHMp3QLnYtWVkQfe9YCBchhazl9bh1UShBhO9SdzxRyDP8No1RbVEMFDD"
}


def extract_product(product_dict: dict):
    """提取产品的相关信息"""
    if product_dict:
        ad_id = product_dict.get('adId')
        metrics = product_dict.get('metrics')

        if metrics:
            spend = metrics.get('adSpend')
            ctr = metrics.get('ctr')
            impressions = metrics.get('impressions')
            roas = metrics.get('roas')
            brandHaloRoas = metrics.get('brandHaloRoas')

        sku = product_dict.get('sku')
        status = product_dict.get('active')
        bid = product_dict.get('bid')
        product_name = product_dict.get('creative').get('name')
        price = product_dict.get('creative').get('price')
        images = product_dict.get('creative').get('images')
        image_url = images.get('standard') if images else None
    data_dict = {
        'ad_id': ad_id if ad_id else None,
        'spend': spend if spend else None,
        'ctr': ctr if ctr else None,
        'impressions': impressions if impressions else None,
        'roas': roas if roas else None,
        'brandHaloRoas': brandHaloRoas if brandHaloRoas else None,
        'sku': sku if sku else None,
        'status': status if status else None,
        'bid(CPC)': bid if bid else None,
        'product_name': product_name if product_name else None,
        'price': f"{float(price):.2f}" if price else None,
        'image': image_url
    }

    return data_dict

def scraper():
    if "uploaded_data" not in st.session_state or not st.session_state.uploaded_data:
        st.warning("尚未上传任何数据，请先在“文件上传页”中完成文件上传。")
        st.stop()    
    data = st.session_state['uploaded_data']
    campaign = data.get('Campaign Summary')
    if campaign is None:
        st.warning("请确认上传Campaign Summary数据")

    # 初始化 product_results
    if 'product_results' not in st.session_state:
        st.session_state['product_results'] = None  # 初始为空
    else:
        if st.session_state['product_results'] is not None:
            # 如果存在有效数据，则显示数据
            st.dataframe(st.session_state['product_results'])
        else:
            st.info("本页面尚未存储任何爬取数据")

    start_button = st.button('开始爬取')
    if start_button:
        with st.spinner("正在爬取数据..."):
            try:
                campaign_ids = campaign['Campaign ID'].unique().tolist()
                responses = {}
                product_results = []
                base_url = "https://us.orangeapronmedia.com/api/v2/store/33602/campaigns/{}/targeting/?page=1&page_size=10"
                base_referer = "https://us.orangeapronmedia.com/r/33602/campaign/details/{}"
                for index, campaign_id in enumerate(campaign_ids):
                    url = base_url.format(campaign_id)
                    headers["referer"] = base_referer.format(campaign_id)

                    response = requests.get(url, headers=headers)

                    if response.status_code != 200:
                        st.write(response.status_code)
                        continue
                    
                    responses[campaign_id] = response.json().get('results')
                    for i in range(len(response.json().get('results'))):

                        product_dict = extract_product(response.json().get('results')[i])

                        product_dict['campaign_id'] = campaign_id

                        product_results.append(product_dict)   

                    time.sleep(2)
                # 清洗 Campaign ID 和 sku
                df = pd.DataFrame(product_results)
                
                st.session_state['product_results'] = df
                st.write(pd.DataFrame(product_results))
            
                # 将爬取结果合并到Promoted Sales
                if "product_results" in st.session_state and 'Promoted Sales' in st.session_state.uploaded_data:
                    product_df = st.session_state['product_results']
                    prom_df = st.session_state.uploaded_data['Promoted Sales']

                    # 建立映射：sku → status
                    keys = list(zip(product_df['campaign_id'], product_df['sku']))
                    values = product_df['status'] 
                    sku_campaign_to_status = dict(zip(keys, values))
                
                    # 然后在 prom_df 中映射
                    prom_df['Promoted OMSID Number'] = prom_df['Promoted OMSID Number'].astype(str)
                    prom_df['Status'] = prom_df.apply(
                        lambda row: sku_campaign_to_status.get((row['Campaign ID'], row['Promoted OMSID Number']), "Not Found"),
                        axis=1
                    )        
                    st.dataframe(prom_df)
                    st.session_state.uploaded_data['Promoted Sales'] = prom_df
                    st.success("已自动将 active状态 应用到 Promoted Sales")
                    
            except Exception as e:
                st.write(e)
                st.write(response.json().get('results'))

scraper()