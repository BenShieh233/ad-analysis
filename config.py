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
        "required_cols": ["Ad Type", "Campaign ID", "Clicks", "Day", "Impressions", "Promoted OMSID Number", "Promoted OMSID Description", "SPA ROAS", 
                          "SPA Sales", "Spend"],
        "preprocess_fn": "promoted",
        "date_col": "Day"
    },
    "HD SKU Map": {
        "skiprows": 0,
        "required_cols": ["OMSID", "MFG Model #", "Weekly Sales QTY", "Promoted Retail", "Inventory", "OMS THD SKU", "Product Name (120)"],
        "preprocess_fn": "map"
    },
    "Purchased Sales": {
        "skiprows": 4,
        "required_cols": ["Ad Type", "Campaign ID", "Customer Type", "Day", "Promoted OMSID Number", "Purchased OMSID Description", "Purchased OMSID Number", 
                          "Purchased SKU Description", "SPA Sales", "Transaction Type"],
        "preprocess_fn": "purchased",
        "date_col": "Day"
    }

}