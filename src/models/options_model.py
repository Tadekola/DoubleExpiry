"""
Options model containing core business logic for the Mechanical Options Trade Recommender.
"""
import logging
from src.utils.helpers import traffic, final_decision
from src.utils.validation import validate_inputs, ValidationError

# Set up logging
logger = logging.getLogger(__name__)

class OptionsModel:
    """
    Core model for options trading recommendations.
    Processes inputs and applies rules to generate status lights and recommendations.
    """

    def __init__(self, inputs):
        """
        Initialize the options model with user inputs.
        
        Args:
            inputs (dict): Dictionary of user inputs from the UI
        """
        self.inputs = inputs
        self.metrics = {}
        self.statuses = {}
        self._validate_inputs()
        
    def _validate_inputs(self):
        """Validate input data to ensure calculations will work correctly."""
        try:
            # Use the validation module to validate all inputs
            validate_inputs(self.inputs)
            logger.info("Input validation passed")
        except ValidationError as e:
            # Log the error and re-raise
            logger.error(f"Input validation failed: {str(e)}")
            raise
    
    def compute_metrics(self):
        """
        Compute derived metrics from user inputs.
        
        Returns:
            dict: Dictionary of computed metrics
            
        Raises:
            ValidationError: If inputs fail validation
        """
        # Extract inputs for easier access
        put_strike = self.inputs['put_strike']
        call_strike = self.inputs['call_strike']
        price = self.inputs['price']
        front_put_iv = self.inputs['front_put_iv']
        front_call_iv = self.inputs['front_call_iv']
        back_put_iv = self.inputs['back_put_iv']
        back_call_iv = self.inputs['back_call_iv']
        atr_points = self.inputs['atr_points']
        use_atr = self.inputs['use_atr']
        
        # Calculate core metrics
        midpoint = (put_strike + call_strike) / 2.0
        dist_from_mid = abs(price - midpoint) / midpoint if midpoint else 1.0  # fraction
        strike_width = abs(call_strike - put_strike)
        
        # Calculate IV metrics
        front_avg_iv = (front_put_iv + front_call_iv) / 2.0
        back_avg_iv = (back_put_iv + back_call_iv) / 2.0
        term_gap_pts = front_avg_iv - back_avg_iv
        
        # Normalize IV rank to 0-1 range
        iv_rank = self.inputs['iv_rank_pct'] / 100.0
        
        # Calculate ATR guard rail
        atr_ok = atr_points <= max(1e-9, strike_width / 2.0)
        
        # Store metrics for later use
        self.metrics = {
            'midpoint': midpoint,
            'dist_from_mid': dist_from_mid,
            'strike_width': strike_width,
            'front_avg_iv': front_avg_iv,
            'back_avg_iv': back_avg_iv,
            'term_gap_pts': term_gap_pts,
            'iv_rank': iv_rank,
            'atr_ok': atr_ok,
            'use_atr': use_atr,
            'atr_points': atr_points
        }
        
        return self.metrics
        
    def evaluate_status_lights(self):
        """
        Evaluate all rule-based status lights.
        
        Returns:
            dict: Dictionary with status labels for each rule
        """
        # Ensure metrics are computed
        if not self.metrics:
            self.compute_metrics()
            
        self.statuses = {}
        
        # Price location rule: within +/-1% ideal, +/-2% acceptable
        self.statuses["Price Location"] = traffic(
            self.metrics['dist_from_mid'],
            green_fn=lambda x: x <= 0.01,
            yellow_fn=lambda x: x <= 0.02,
        )
        
        # Term structure rule: front avg IV at least 2 pts over back avg IV
        self.statuses["Term Structure"] = traffic(
            self.metrics['term_gap_pts'],
            green_fn=lambda x: x >= 2.0,
            yellow_fn=lambda x: x >= 1.0,
        )
        
        # IV Rank rule: 30-50% ideal; 20-29% or 51-60% caution
        self.statuses["IV Rank"] = traffic(
            self.metrics['iv_rank'],
            green_fn=lambda x: 0.30 <= x <= 0.50,
            yellow_fn=lambda x: (0.20 <= x < 0.30) or (0.50 < x <= 0.60),
        )
        
        # Event proximity: 3-7 days ideal; 1-2 days caution
        self.statuses["Event Proximity"] = traffic(
            self.inputs['days_to_event'],
            green_fn=lambda x: 3 <= x <= 7,
            yellow_fn=lambda x: 1 <= x <= 2,
        )
        
        # VIX band: 14-20 ideal; 20-25 caution
        self.statuses["VIX"] = traffic(
            self.inputs['vix_value'],
            green_fn=lambda x: 14 <= x <= 20,
            yellow_fn=lambda x: 20 < x <= 25,
        )
        
        # Optional ATR guardrail
        if self.inputs['use_atr']:
            self.statuses["ATR Guardrail"] = traffic(
                self.metrics['atr_ok'],
                green_fn=lambda ok: ok is True,
                yellow_fn=lambda ok: False,  # no yellow state; either OK or RED
            )
            
        return self.statuses
    
    def get_final_decision(self):
        """
        Get the final trading decision based on status lights.
        
        Returns:
            str: Final decision text
        """
        if not self.statuses:
            self.evaluate_status_lights()
            
        return final_decision(self.statuses)
    
    def get_strategy_suggestions(self):
        """
        Generate trading strategy suggestions based on current conditions.
        
        Returns:
            list: List of strategy suggestions
        """
        # Ensure metrics and statuses are computed
        if not self.metrics:
            self.compute_metrics()
        if not self.statuses:
            self.evaluate_status_lights()
            
        suggestions = []
        iv_rank = self.metrics['iv_rank']
        vix_value = self.inputs['vix_value']
        
        # Apply rules for strategy suggestions
        if (self.statuses.get("IV Rank") == "GREEN" and 
            self.statuses.get("Term Structure") in ("GREEN", "YELLOW") and 
            self.statuses.get("Price Location") != "RED"):
            suggestions.append("Double Calendar (front week vs back week)")
            
        if iv_rank < 0.25 and self.statuses.get("Price Location") == "GREEN":
            suggestions.append("Cheaper OTM Vertical (directional)")
            
        if (0.45 < iv_rank <= 0.60 and 
            vix_value >= 18 and 
            self.statuses.get("Price Location") == "GREEN"):
            suggestions.append("Short-duration Iron Condor (range)")
            
        if not suggestions:
            suggestions.append("No trade — wait for better IV/term structure or re-center strikes")
            
        return suggestions
