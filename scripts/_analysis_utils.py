"""
Analysis utilities for ACD collusion detection.
Provides standardized data processing functions to prevent silent failures.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def inclusive_end_date(end_date: str) -> datetime:
    """
    Convert YYYY-MM-DD string to inclusive end datetime (23:59:59).
    
    Args:
        end_date: Date string in YYYY-MM-DD format
        
    Returns:
        datetime at 23:59:59 of the specified date
        
    Example:
        >>> inclusive_end_date("2025-09-26")
        datetime(2025, 9, 26, 23, 59, 59)
    """
    try:
        # Parse the date and add 23:59:59 to make it inclusive
        base_date = datetime.strptime(end_date, "%Y-%m-%d")
        return base_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    except ValueError as e:
        logger.error(f"Invalid date format '{end_date}': {e}")
        raise ValueError(f"Invalid date format '{end_date}'. Expected YYYY-MM-DD.")


def ensure_time_mid_volume(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize DataFrame columns to standard schema: [time, mid, volume].
    
    Args:
        df: DataFrame with potential column name variations
        
    Returns:
        DataFrame with standardized columns [time, mid, volume]
        
    Column mapping:
        - time: timestamp, ts, datetime, date
        - mid: mid, price, close, last_price
        - volume: volume, size, last_trade_qty, qty
    """
    if df.empty:
        logger.warning("Empty DataFrame provided to ensure_time_mid_volume")
        return df
    
    # Create a copy to avoid modifying original
    result_df = df.copy()
    
    # Time column mapping
    time_cols = ['timestamp', 'ts', 'datetime', 'date', 'time']
    time_col = None
    for col in time_cols:
        if col in result_df.columns:
            time_col = col
            break
    
    if time_col is None:
        raise ValueError("No time column found. Expected one of: timestamp, ts, datetime, date, time")
    
    # Rename time column
    if time_col != 'time':
        result_df = result_df.rename(columns={time_col: 'time'})
    
    # Ensure time is datetime64[ns] and sorted
    if not pd.api.types.is_datetime64_any_dtype(result_df['time']):
        result_df['time'] = pd.to_datetime(result_df['time'])
    
    result_df = result_df.sort_values('time').reset_index(drop=True)
    
    # Mid column mapping (price, close, last_price, mid)
    mid_cols = ['mid', 'price', 'close', 'last_price', 'last_trade_px']
    mid_col = None
    for col in mid_cols:
        if col in result_df.columns:
            mid_col = col
            break
    
    if mid_col is None:
        # Try to derive mid from bid/ask
        if 'best_bid' in result_df.columns and 'best_ask' in result_df.columns:
            result_df['mid'] = (result_df['best_bid'] + result_df['best_ask']) / 2
            logger.info("Derived mid from best_bid and best_ask")
        else:
            raise ValueError("No mid/price column found and cannot derive from bid/ask")
    else:
        # Rename mid column
        if mid_col != 'mid':
            result_df = result_df.rename(columns={mid_col: 'mid'})
    
    # Volume column mapping
    volume_cols = ['volume', 'size', 'last_trade_qty', 'qty']
    volume_col = None
    for col in volume_cols:
        if col in result_df.columns:
            volume_col = col
            break
    
    if volume_col is None:
        # Set volume to 1.0 if not found (for price-only data)
        result_df['volume'] = 1.0
        logger.warning("No volume column found, setting volume to 1.0")
    else:
        # Rename volume column
        if volume_col != 'volume':
            result_df = result_df.rename(columns={volume_col: 'volume'})
    
    # Ensure we have the required columns
    required_cols = ['time', 'mid', 'volume']
    missing_cols = [col for col in required_cols if col not in result_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns after normalization: {missing_cols}")
    
    # Drop rows with NaN values in required columns
    initial_rows = len(result_df)
    result_df = result_df.dropna(subset=required_cols)
    dropped_rows = initial_rows - len(result_df)
    if dropped_rows > 0:
        logger.warning(f"Dropped {dropped_rows} rows with NaN values in required columns")
    
    logger.info(f"Normalized DataFrame: {len(result_df)} rows, columns: {list(result_df.columns)}")
    return result_df


def resample_minute(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample DataFrame to 1-minute bars using proper pandas syntax.
    
    Args:
        df: DataFrame with 'time' as index and 'mid', 'volume' columns
        
    Returns:
        DataFrame with 1-minute OHLCV bars
    """
    if df.empty:
        logger.warning("Empty DataFrame provided to resample_minute")
        return df
    
    # Ensure time is the index
    if 'time' not in df.index.names and 'time' in df.columns:
        df = df.set_index('time')
    
    # Use proper pandas resample syntax
    try:
        # Resample to 1-minute bars
        resampled = df.resample('1T').agg({
            'mid': ['first', 'last', 'min', 'max'],
            'volume': 'sum'
        })
        
        # Flatten column names
        resampled.columns = ['open', 'close', 'low', 'high', 'volume']
        
        # Add mid as average of OHLC
        resampled['mid'] = (resampled['open'] + resampled['close'] + resampled['low'] + resampled['high']) / 4
        
        # Drop NaN rows
        resampled = resampled.dropna()
        
        # Reset index to get time as column
        resampled = resampled.reset_index()
        
        logger.info(f"Resampled to {len(resampled)} 1-minute bars")
        return resampled
        
    except Exception as e:
        logger.error(f"Error in resample_minute: {e}")
        raise


def resample_second(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample DataFrame to 1-second bars using proper pandas syntax.
    
    Args:
        df: DataFrame with 'time' as index and 'mid', 'volume' columns
        
    Returns:
        DataFrame with 1-second OHLCV bars
    """
    if df.empty:
        logger.warning("Empty DataFrame provided to resample_second")
        return df
    
    # Ensure time is the index
    if 'time' not in df.index.names and 'time' in df.columns:
        df = df.set_index('time')
    
    # Use proper pandas resample syntax
    try:
        # Resample to 1-second bars
        resampled = df.resample('1S').agg({
            'mid': ['first', 'last', 'min', 'max'],
            'volume': 'sum'
        })
        
        # Flatten column names
        resampled.columns = ['open', 'close', 'low', 'high', 'volume']
        
        # Add mid as average of OHLC
        resampled['mid'] = (resampled['open'] + resampled['close'] + resampled['low'] + resampled['high']) / 4
        
        # Drop NaN rows
        resampled = resampled.dropna()
        
        # Reset index to get time as column
        resampled = resampled.reset_index()
        
        logger.info(f"Resampled to {len(resampled)} 1-second bars")
        return resampled
        
    except Exception as e:
        logger.error(f"Error in resample_second: {e}")
        raise


def validate_dataframe(df: pd.DataFrame, required_cols: list = None) -> bool:
    """
    Validate DataFrame has required structure for analysis.
    
    Args:
        df: DataFrame to validate
        required_cols: List of required columns (default: ['time', 'mid', 'volume'])
        
    Returns:
        True if valid, raises ValueError if not
    """
    if required_cols is None:
        required_cols = ['time', 'mid', 'volume']
    
    if df.empty:
        raise ValueError("DataFrame is empty")
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Check for NaN values in required columns
    nan_counts = df[required_cols].isna().sum()
    if nan_counts.any():
        raise ValueError(f"NaN values found in required columns: {nan_counts.to_dict()}")
    
    # Check data types
    if not pd.api.types.is_datetime64_any_dtype(df['time']):
        raise ValueError("Time column is not datetime type")
    
    if not pd.api.types.is_numeric_dtype(df['mid']):
        raise ValueError("Mid column is not numeric type")
    
    if not pd.api.types.is_numeric_dtype(df['volume']):
        raise ValueError("Volume column is not numeric type")
    
    logger.info(f"DataFrame validation passed: {len(df)} rows, columns: {list(df.columns)}")
    return True


def expected_rows(start: datetime, end: datetime, freq: str = 'S') -> int:
    """
    Calculate expected number of rows for a time window.
    
    Args:
        start: Start datetime
        end: End datetime (inclusive)
        freq: Frequency ('S' for seconds, 'T' for minutes)
        
    Returns:
        Expected number of rows
    """
    if freq == 'S':
        return int((end - start).total_seconds()) + 1
    elif freq == 'T':
        return int((end - start).total_seconds() / 60) + 1
    else:
        raise ValueError(f"Unsupported frequency: {freq}")


def compute_coverage(df: pd.DataFrame, start: datetime, end: datetime, freq: str = 'S') -> float:
    """
    Compute coverage ratio for a DataFrame within a time window.
    
    Args:
        df: DataFrame with time index
        start: Start datetime
        end: End datetime (inclusive)
        freq: Frequency ('S' for seconds, 'T' for minutes)
        
    Returns:
        Coverage ratio (0.0 to 1.0)
    """
    if df.empty:
        return 0.0
    
    expected = expected_rows(start, end, freq)
    actual = len(df.index.unique())
    return round(min(actual / expected, 1.0), 4)
