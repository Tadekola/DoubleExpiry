"""
Helper functions for the Mechanical Options Trade Recommender application.
"""

def status_color(label):
    """
    Returns CSS styling for status labels based on their value.
    
    Args:
        label (str): Status label (GREEN, YELLOW, RED)
        
    Returns:
        str: CSS style string
    """
    colors = {
        "GREEN": "#C6EFCE", 
        "YELLOW": "#FFF2CC", 
        "RED": "#F8CBAD"
    }
    return f"background-color:{colors.get(label,'#FFFFFF')}; padding:6px; border-radius:6px;"

def traffic(value, green_fn, yellow_fn):
    """
    Apply traffic light logic to determine status based on provided criteria.
    
    Args:
        value: The value to evaluate
        green_fn: Function that returns True if value meets GREEN criteria
        yellow_fn: Function that returns True if value meets YELLOW criteria
        
    Returns:
        str: Status label (GREEN, YELLOW, or RED)
    """
    if green_fn(value):
        return "GREEN"
    elif yellow_fn(value):
        return "YELLOW"
    else:
        return "RED"

def final_decision(statuses):
    """
    Determine final trading decision based on status lights.
    
    Args:
        statuses (dict): Dictionary of status lights
        
    Returns:
        str: Final decision string
    """
    score_map = {"GREEN": 2, "YELLOW": 1, "RED": 0}
    score = sum(score_map[s] for s in statuses.values())
    reds = sum(1 for s in statuses.values() if s == "RED")
    n = len(statuses)
    
    if score == 2 * n and reds == 0:
        return "ENTER (All green) ✅"
    elif score >= 2 * (n - 1) and reds == 0:
        return "ENTER — CAUTION ⚠️"
    else:
        return "WAIT ❌"

def load_config():
    """
    Load configuration settings for the application.
    
    Returns:
        dict: Configuration settings
    """
    # In the future, this could load from a config file
    return {
        "symbols": ["SPY", "QQQ", "IWM"],
        "default_symbol": "SPY",
        "default_price": 635.0,
    }
