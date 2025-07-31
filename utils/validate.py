import pandas as pd


def validate_dataframe(df: pd.DataFrame, required_cols: list[str]) -> list[str]:
    """检查 df 中缺失哪些必需列，返回缺失列名列表。"""
    return [c for c in required_cols if c not in df.columns]