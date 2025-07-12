"""
Market hours and scheduling utilities.

This module provides functions to determine market hours, trading days,
and schedule calculations.
"""
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import pandas_market_calendars as mcal
import pytz
from rich.console import Console

# Initialize rich console
console = Console()

# Timezone for market hours (Eastern Time)
NYC = pytz.timezone("America/New_York")
UTC = pytz.utc

# Market hours (in Eastern Time)
MARKET_OPEN = time(9, 30)  # 9:30 AM ET
MARKET_CLOSE = time(16, 0)  # 4:00 PM ET

# Number of minutes in a trading day
TRADING_DAY_MINUTES = 390  # 6.5 hours * 60 minutes


def get_market_calendar() -> mcal.MarketCalendar:
    """Get the NYSE market calendar.
    
    Returns:
        mcal.MarketCalendar: NYSE market calendar instance
    """
    return mcal.get_calendar('NYSE')


def is_market_open(timestamp: Optional[datetime] = None) -> Tuple[bool, Optional[datetime]]:
    """Check if the market is currently open.
    
    Args:
        timestamp: Optional datetime to check (defaults to now).
            Can be timezone-naive (assumed ET) or timezone-aware.
            
    Returns:
        Tuple[bool, Optional[datetime]]: 
            - bool: True if market is open, False otherwise
            - datetime: Next market open time (if market is closed), None if market is open
    """
    if timestamp is None:
        timestamp = datetime.now(NYC)
    elif timestamp.tzinfo is None:
        # Assume ET if timezone-naive
        timestamp = NYC.localize(timestamp)
    else:
        # Convert to ET
        timestamp = timestamp.astimezone(NYC)
    
    # Get market calendar
    cal = get_market_calendar()
    
    # Get market schedule for today
    schedule = cal.schedule(
        start_date=timestamp.date() - timedelta(days=1),
        end_date=timestamp.date() + timedelta(days=7)
    )
    
    if schedule.empty:
        # No market days in the schedule (holiday break?)
        next_open = timestamp + timedelta(days=1)
        next_open = next_open.replace(hour=9, minute=30, second=0, microsecond=0)
        return False, next_open
    
    # Check if today is a trading day
    today = timestamp.date()
    today_str = today.strftime('%Y-%m-%d')
    
    if today_str not in schedule.index:
        # Today is not a trading day, find next trading day
        next_trading_day = schedule[schedule.index > today_str].iloc[0]
        next_open = next_trading_day['market_open'].to_pydatetime()
        return False, next_open
    
    # Get today's market hours
    trading_day = schedule.loc[today_str]
    market_open = trading_day['market_open'].to_pydatetime()
    market_close = trading_day['market_close'].to_pydatetime()
    
    # Check if current time is within market hours
    if market_open <= timestamp <= market_close:
        return True, None
    
    # Market is closed, find next open
    if timestamp < market_open:
        # Market opens later today
        return False, market_open
    else:
        # Market closed for today, find next trading day
        next_trading_day = schedule[schedule.index > today_str].iloc[0]
        next_open = next_trading_day['market_open'].to_pydatetime()
        return False, next_open


def get_next_market_open(timestamp: Optional[datetime] = None) -> datetime:
    """Get the next market open time.
    
    Args:
        timestamp: Optional reference datetime (defaults to now).
            Can be timezone-naive (assumed ET) or timezone-aware.
            
    Returns:
        datetime: Next market open time (timezone-aware in ET)
    """
    if timestamp is None:
        timestamp = datetime.now(NYC)
    elif timestamp.tzinfo is None:
        # Assume ET if timezone-naive
        timestamp = NYC.localize(timestamp)
    else:
        # Convert to ET
        timestamp = timestamp.astimezone(NYC)
    
    # Check if market is currently open
    is_open, next_open = is_market_open(timestamp)
    
    if is_open:
        # Market is open now, next open is tomorrow
        next_day = (timestamp + timedelta(days=1)).date()
        next_open = NYC.localize(datetime.combine(next_day, MARKET_OPEN))
        return next_open
    
    # Return the next open time from is_market_open
    return next_open


def get_market_hours(date_obj: Optional[date] = None) -> Tuple[datetime, datetime]:
    """Get the market open and close times for a specific date.
    
    Args:
        date_obj: Date to check (defaults to today).
            
    Returns:
        Tuple[datetime, datetime]: 
            - Market open time (timezone-aware in ET)
            - Market close time (timezone-aware in ET)
            
    Raises:
        ValueError: If the specified date is not a trading day
    """
    if date_obj is None:
        date_obj = datetime.now(NYC).date()
    
    # Get market calendar
    cal = get_market_calendar()
    
    # Get market schedule for the date
    schedule = cal.schedule(
        start_date=date_obj - timedelta(days=1),
        end_date=date_obj + timedelta(days=1)
    )
    
    date_str = date_obj.strftime('%Y-%m-%d')
    if date_str not in schedule.index:
        raise ValueError(f"{date_obj} is not a trading day")
    
    trading_day = schedule.loc[date_str]
    return trading_day['market_open'], trading_day['market_close']


def get_trading_days(start_date: date, end_date: date) -> pd.DatetimeIndex:
    """Get all trading days between two dates (inclusive).
    
    Args:
        start_date: Start date
        end_date: End date (inclusive)
        
    Returns:
        pd.DatetimeIndex: Trading days in the range
    """
    cal = get_market_calendar()
    schedule = cal.schedule(start_date=start_date, end_date=end_date)
    return schedule.index


def is_trading_day(date_obj: date) -> bool:
    """Check if a date is a trading day.
    
    Args:
        date_obj: Date to check
        
    Returns:
        bool: True if it's a trading day, False otherwise
    """
    cal = get_market_calendar()
    schedule = cal.schedule(
        start_date=date_obj - timedelta(days=1),
        end_date=date_obj + timedelta(days=1)
    )
    return date_obj.strftime('%Y-%m-%d') in schedule.index
