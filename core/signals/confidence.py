"""
Dynamic Confidence Threshold Module.

This module provides functionality for calculating dynamic confidence thresholds
based on historical volatility using either z-score or quantile methods.
"""
import logging
from typing import Tuple, Optional
import numpy as np
import pandas as pd

from core.config import console
from core.config.constants import WINDOW_CONF, Z_MIN, QUANTILE_MIN, USE_QUANTILE, USE_DYNAMIC_CONFIDENCE

# Configure logger
logger = logging.getLogger(__name__)

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
    fixed_threshold: Optional[float] = None,
    use_dynamic_confidence: Optional[bool] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Apply confidence threshold filtering to signals.
    
    Args:
        df: DataFrame containing signals and confidence values
        confidence_col: Name of the column containing confidence values
        signal_col: Name of the column containing signals
        fixed_threshold: Fixed threshold to use if not using dynamic confidence
        use_dynamic_confidence: Whether to use dynamic confidence thresholds
        **kwargs: Additional arguments passed to calculate_dynamic_threshold
        
    Returns:
        DataFrame with updated signals based on confidence threshold
    """
    """
    Apply confidence threshold filtering to signals.
    
    Args:
        df: DataFrame containing signals and confidence values
        confidence_col: Name of the column containing confidence values
        signal_col: Name of the column containing signals
        fixed_threshold: If provided and USE_DYNAMIC_CONFIDENCE is False, use this fixed threshold
        **kwargs: Additional arguments passed to calculate_dynamic_threshold
        
    Returns:
        DataFrame with updated signals based on confidence threshold
    """
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # Determine which confidence type to use
    use_dynamic = USE_DYNAMIC_CONFIDENCE if use_dynamic_confidence is None else use_dynamic_confidence
    
    # Initialize default values
    thresholds = pd.Series(fixed_threshold if fixed_threshold is not None else 0.005, index=df.index)
    method = 'default'
    
    try:
        if use_dynamic:
            # Calculate dynamic thresholds
            thresholds, method = calculate_dynamic_threshold(
                df[confidence_col],
                **kwargs
            )
            df['threshold_used'] = thresholds
            df['threshold_method'] = method
        else:
            # Use fixed threshold
            if fixed_threshold is None:
                # Fall back to the first value from kwargs or a default
                fixed_threshold = kwargs.get('fallback_threshold', 0.005)
            thresholds = pd.Series(fixed_threshold, index=df.index)
            df['threshold_used'] = fixed_threshold
            method = f"fixed ({fixed_threshold:.6f})"
            df['threshold_method'] = method
    except Exception as e:
        console.print(f"[yellow]Warning in apply_confidence_filter: {str(e)}[/yellow]")
        if 'threshold_used' not in df.columns:
            df['threshold_used'] = fixed_threshold if fixed_threshold is not None else 0.005
        if 'threshold_method' not in df.columns:
            df['threshold_method'] = 'error_default'
    
    # Apply threshold filter (only keep signals above threshold)
    try:
        # Extract confidence values and signals, ensuring confidence is numeric
        conf_values = pd.to_numeric(df[confidence_col], errors='coerce')
        if conf_values.isna().any():
            logger.warning(f"Converted {conf_values.isna().sum()} non-numeric confidence values to NaN")
        signal_values = df[signal_col]
        
        # Debug log the confidence values
        logger.debug(f"Confidence values dtype: {conf_values.dtype}")
        logger.debug(f"Confidence values sample: {conf_values.head()}")
        
        thresh_values = thresholds.values if hasattr(thresholds, 'values') else thresholds
        
        # Create mask for low confidence signals (that aren't already 'STAY')
        mask_low_confidence = (conf_values < thresh_values) & (signal_values != 'STAY')
        
        # Apply the mask to update signals
        df.loc[mask_low_confidence, signal_col] = 'STAY'
    except Exception as e:
        console.print(f"[red]Error applying confidence filter: {e}")
        # If there's an error, fall back to keeping signals as is
        pass
    
    # Add threshold method to the first row for reference
    if not df.empty:
        df.loc[df.index[0], 'threshold_method'] = method
    
    return df
