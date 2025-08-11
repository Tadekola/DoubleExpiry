"""
Validation utilities for the Mechanical Options Trade Recommender.
"""

class ValidationError(Exception):
    """Custom exception for input validation errors."""
    pass

def validate_positive(value, name):
    """
    Validate that a value is positive.
    
    Args:
        value: The value to check
        name: Name of the value for error message
        
    Raises:
        ValidationError: If the value is not positive
    """
    if value <= 0:
        raise ValidationError(f"{name} must be greater than zero")
    return value

def validate_range(value, name, min_val=None, max_val=None):
    """
    Validate that a value is within a specified range.
    
    Args:
        value: The value to check
        name: Name of the value for error message
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        
    Raises:
        ValidationError: If the value is outside the specified range
    """
    if min_val is not None and value < min_val:
        raise ValidationError(f"{name} must be at least {min_val}")
    if max_val is not None and value > max_val:
        raise ValidationError(f"{name} must be at most {max_val}")
    return value

def validate_strikes(put_strike, call_strike):
    """
    Validate that put strike is less than call strike.
    
    Args:
        put_strike: Put option strike price
        call_strike: Call option strike price
        
    Raises:
        ValidationError: If the put strike is greater than or equal to call strike
    """
    if put_strike >= call_strike:
        raise ValidationError("Put strike should be less than call strike for typical strategies")
    return True

def validate_inputs(inputs):
    """
    Validate all user inputs.
    
    Args:
        inputs (dict): Dictionary of user inputs
        
    Returns:
        dict: Validated inputs (same as input if all validations pass)
        
    Raises:
        ValidationError: If any validation fails
    """
    # Validate basic numeric inputs
    validate_positive(inputs['price'], "Price")
    validate_positive(inputs['put_strike'], "Put strike")
    validate_positive(inputs['call_strike'], "Call strike")
    
    # Validate strike relationship
    validate_strikes(inputs['put_strike'], inputs['call_strike'])
    
    # Validate IV values
    validate_range(inputs['front_put_iv'], "Front-week PUT IV", min_val=0)
    validate_range(inputs['front_call_iv'], "Front-week CALL IV", min_val=0)
    validate_range(inputs['back_put_iv'], "Back-week PUT IV", min_val=0)
    validate_range(inputs['back_call_iv'], "Back-week CALL IV", min_val=0)
    
    # Validate other market data
    validate_range(inputs['iv_rank_pct'], "IV Rank", min_val=0, max_val=100)
    validate_range(inputs['days_to_event'], "Days to event", min_val=0)
    validate_positive(inputs['vix_value'], "VIX value")
    
    # ATR validation
    if inputs['use_atr']:
        validate_positive(inputs['atr_points'], "ATR points")
    
    return inputs
