from __future__ import annotations

import pandas as pd
from typing import Dict, Tuple, Optional

from .backtesting import evaluate_individual_indicators


def get_best_indicator(
    ticker: str,
    df: pd.DataFrame,
    params: Dict[str, int | float],
    interval: str,
    money: float,
    metric: str = "Keuntungan (%)",
) -> Tuple[Optional[Dict[str, float]], pd.DataFrame]:
    """Kembalikan indikator terbaik dan tabel evaluasi penuh.

    Parameters
    ----------
    ticker : str
        Kode saham.
    df : pd.DataFrame
        Data harga yang telah difilter.
    params : dict
        Parameter perhitungan indikator.
    interval : str
        Interval data (misal '1 day').
    money : float
        Modal awal simulasi backtesting.
    metric : str, default 'Keuntungan (%)'
        Kolom metrik yang dijadikan acuan pemilihan.

    Returns
    -------
    tuple
        (baris terbaik sebagai dict atau None, dataframe hasil evaluasi)
    """
    result = evaluate_individual_indicators(ticker, df, params, interval, money)
    if result.empty:
        return None, result

    if metric in result.columns and result[metric].notna().any():
        result_sorted = result.sort_values(by=metric, ascending=False)
    else:
        result_sorted = result

    best_row = result_sorted.iloc[0].to_dict()
    return best_row, result_sorted