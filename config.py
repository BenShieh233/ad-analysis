file_configs = {
    "Campaign Summary": {
        "skiprows": 4,
        "required_cols": ["Interval", "Ad Type", "Campaign ID", "Campaign Name", "Status", "Click Through Rate (CTR) (sum)", "Clicks (sum)",
                          "Cost Per Click (CPC) (sum)", "Cost Per Thousand Views (CPM) (sum)", "Impressions (sum)", "Return on Ad Spend (ROAS) SPA (sum)",
                          "SPA In-Store Sales (sum)", "SPA Online Sales (sum)", "SPA Sales (sum)", "Spend (sum)"],
        "preprocess_fn": "campaign",
        "date_col": "Interval"
    },
    "Promoted Sales": {
        "skiprows": 4,
        "required_cols": ["Ad Type", "Campaign ID", "Clicks", "Day", "Impressions", "Month", "Month Name", "Promoted OMSID", "SPA ROAS", 
                          "SPA Sales", "Spend", "Week", "Year"],
        "preprocess_fn": "promoted",
        "date_col": "Day"
    },
    "HD SKU Map": {
        "skiprows": 0,
        "required_cols": ["OMSID", "MFG Model #", "OMS THD SKU", "Product Name (120)"],
        "preprocess_fn": "map"
    },

}