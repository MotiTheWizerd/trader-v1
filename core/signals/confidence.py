"""
Dynamic Confidence Threshold Module.

This module provides functionality for calculating dynamic confidence thresholds
based on historical volatility using either z-score or quantile methods.
"""
from typing import Tuple, Optional
import numpy as np
import pandas as pd

from core.config.constants import WINDOW_CONF, Z_MIN, QUANTILE_MIN, USE_QUANTILE

def calculate_dynamic_threshold(
    values: pd.Series,
    window: int = WINDOW_CONF,
    z_min: float = Z_MIN,
    quantile_min: float = QUANTILE_MIN,
    use_quantile: bool = USE_QUANTILE,
    fallback_threshold: float = 0.005
) -> Tuple[pd.Series, str]:
    """
    Calculate dynamic confidence threshold based on historical volatility.
    
    Args:
        values: Series of confidence values
        window: Rolling window size for calculating statistics
        z_min: Minimum z-score for dynamic threshold (when use_quantile=False)
        quantile_min: Quantile to use for threshold (when use_quantile=True)
        use_quantile: Whether to use quantile-based thresholding
        fallback_threshold: Fallback threshold when not enough data or zero volatility
        
    Returns:
        Tuple containing:
        - Series of dynamic thresholds
        - String describing the threshold method used
    """
    # Initialize output series with fallback threshold
    thresholds = pd.Series(index=values.index, dtype=float)
    
    # Calculate rolling statistics
    rolling_mean = values.rolling(window=window, min_periods=1).mean()
    rolling_std = values.rolling(window=window, min_periods=1).std()
    
    # Calculate threshold based on selected method
    if use_quantile:
        # Use quantile-based threshold
        rolling_q = values.rolling(window=window, min_periods=1).quantile(quantile_min)
        thresholds = rolling_q
        method = f"{int(quantile_min*100)}th percentile"
    else:
        # Use z-score based threshold
        thresholds = rolling_mean + (z_min * rolling_std)
        method = f"mean + {z_min}σ"
    
    # Apply fallback where needed (not enough data or zero volatility)
    mask_fallback = (values.index < window) | (rolling_std == 0)
    thresholds.loc[mask_fallback] = fallback_threshold
    
    return thresholds, method

def apply_confidence_filter(
    df: pd.DataFrame,
    confidence_col: str = 'confidence',
    signal_col: str = 'signal',
    **kwargs
) -> pd.DataFrame:
    """
    Apply dynamic confidence threshold filtering to signals.
    
    Args:
        df: DataFrame containing signals and confidence values
        confidence_col: Name of the column containing confidence values
        signal_col: Name of the column containing signals
        **kwargs: Additional arguments passed to calculate_dynamic_threshold
        
    Returns:
        DataFrame with updated signals based on dynamic threshold
    """
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # Calculate dynamic thresholds
    thresholds, method = calculate_dynamic_threshold(
        df[confidence_col],
        **kwargs
    )
    
    # Store the threshold values for analysis
    df['threshold_used'] = thresholds
    
    # Apply threshold filter (only keep signals above threshold)
    mask_low_confidence = (df[confidence_col] < thresholds) & (df[signal_col] != 'STAY')
    df.loc[mask_low_confidence, signal_col] = 'STAY'
    
    # Add threshold method to the first row for reference
    if not df.empty:
        df.loc[df.index[0], 'threshold_method'] = method
    
    return df
