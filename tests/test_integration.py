"""
Integration testing for the Mechanical Options Trade Recommender application.

This module provides tests that verify the integration between different
components of the application, focusing on data flow and state management.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
from src.models.options_model import OptionsModel
from src.utils.helpers import traffic, status_color
from src.utils.validation import validate_inputs, ValidationError


class IntegrationTests(unittest.TestCase):
    """Test integration between different components of the options app."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a valid set of inputs for testing
        self.valid_inputs = {
            "symbol": "SPY", 
            "price": 435.0,
            "put_strike": 425.0,
            "call_strike": 445.0,
            "front_put_iv": 20.0,
            "front_call_iv": 19.0,
            "back_put_iv": 18.0, 
            "back_call_iv": 17.0,
            "iv_rank_pct": 45.0,
            "days_to_event": 5,
            "vix_value": 16.5,
            "atr_points": 4.5,
            "use_atr": True
        }
    
    def test_validation_to_model_integration(self):
        """Test that validation results properly flow into the model."""
        # Test with valid inputs - should not raise exception
        try:
            # Validate inputs first
            validate_inputs(self.valid_inputs)
            
            # Then pass to model
            model = OptionsModel(self.valid_inputs)
            metrics = model.compute_metrics()
            self.assertIsNotNone(metrics)
            
        except ValidationError:
            self.fail("Valid inputs raised ValidationError unexpectedly")
        
        # Test with invalid inputs - should raise exception
        invalid_inputs = self.valid_inputs.copy()
        invalid_inputs["front_put_iv"] = -10.0  # Invalid negative value
        
        with self.assertRaises(ValidationError):
            validate_inputs(invalid_inputs)
            model = OptionsModel(invalid_inputs)
    
    def test_helpers_to_model_integration(self):
        """Test that helper functions properly integrate with the model."""
        # Create model
        model = OptionsModel(self.valid_inputs)
        metrics = model.compute_metrics()
        
        # Test traffic light logic with model data
        dist_pct = metrics["dist_from_mid"] * 100
        
        # Recreate the traffic light logic from the model
        position_status = traffic(
            dist_pct,
            lambda x: x <= 1.0,        # Green condition 
            lambda x: 1.0 < x <= 2.0   # Yellow condition
        )
        
        # Get status from model directly
        statuses = model.evaluate_status_lights()
        model_position_status = statuses["Price Position"]
        
        # Verify they match
        self.assertEqual(position_status, model_position_status)
        
        # Test status color helper
        for status in ["GREEN", "YELLOW", "RED"]:
            color_style = status_color(status)
            self.assertIsNotNone(color_style)
            self.assertTrue("background-color" in color_style)
    
    def test_full_workflow_integration(self):
        """Test the complete workflow from inputs to final decision."""
        # Create model with valid inputs
        model = OptionsModel(self.valid_inputs)
        
        # Run the full workflow
        metrics = model.compute_metrics()
        statuses = model.evaluate_status_lights()
        decision = model.get_final_decision()
        suggestions = model.get_strategy_suggestions()
        
        # Verify integrated results
        # 1. Check that metrics values are used in status evaluation
        iv_status = statuses["IV Level"]
        self.assertIn(iv_status, ["GREEN", "YELLOW", "RED"])
        
        # 2. Check that statuses influence the final decision
        if all(status == "GREEN" for status in statuses.values()):
            self.assertTrue("ENTER" in decision and "All green" in decision)
        elif "RED" in statuses.values():
            self.assertTrue("WAIT" in decision)
        
        # 3. Check that decision influences strategy suggestions
        if "WAIT" in decision:
            # Should have limited or no suggestions when decision is WAIT
            self.assertTrue(len(suggestions) <= 1)


if __name__ == "__main__":
    unittest.main()
