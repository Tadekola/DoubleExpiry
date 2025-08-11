"""
End-to-End testing for the Mechanical Options Trade Recommender application.

This module provides automated tests that simulate user interactions with the
Streamlit app and verify the application's behavior in an integrated manner.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import streamlit as st

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import application modules
from src.models.options_model import OptionsModel
from src.utils.validation import ValidationError


class EndToEndTests(unittest.TestCase):
    """Test end-to-end functionality of the options app."""
    
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
    
    def test_valid_input_flow(self):
        """Test the complete flow with valid inputs."""
        # Create model with valid inputs
        model = OptionsModel(self.valid_inputs)
        
        # Test metrics computation
        metrics = model.compute_metrics()
        self.assertIsNotNone(metrics)
        self.assertTrue("midpoint" in metrics)
        self.assertTrue("dist_from_mid" in metrics)
        self.assertTrue("strike_width" in metrics)
        self.assertTrue("front_avg_iv" in metrics)
        self.assertTrue("back_avg_iv" in metrics)
        
        # Test status lights evaluation
        statuses = model.evaluate_status_lights()
        self.assertIsNotNone(statuses)
        self.assertTrue("Strike Width" in statuses)
        self.assertTrue("Price Position" in statuses)
        self.assertTrue("IV Level" in statuses)
        self.assertTrue("Event Risk" in statuses)
        self.assertTrue("Term Structure" in statuses)
        
        # Test final decision
        decision = model.get_final_decision()
        self.assertIsNotNone(decision)
        self.assertTrue(any(x in decision for x in ["ENTER", "WAIT"]))
        
        # Test strategy suggestions
        suggestions = model.get_strategy_suggestions()
        self.assertIsInstance(suggestions, list)
    
    def test_invalid_inputs(self):
        """Test handling of invalid inputs."""
        # Test with price below put strike
        invalid_inputs = self.valid_inputs.copy()
        invalid_inputs["price"] = 420.0  # Below put strike
        
        with self.assertRaises(ValidationError):
            model = OptionsModel(invalid_inputs)
            model.compute_metrics()
            
        # Test with negative IV
        invalid_inputs = self.valid_inputs.copy()
        invalid_inputs["front_put_iv"] = -5.0
        
        with self.assertRaises(ValidationError):
            model = OptionsModel(invalid_inputs)
            model.compute_metrics()
            
        # Test with put strike above call strike
        invalid_inputs = self.valid_inputs.copy()
        invalid_inputs["put_strike"] = 450.0
        invalid_inputs["call_strike"] = 440.0
        
        with self.assertRaises(ValidationError):
            model = OptionsModel(invalid_inputs)
            model.compute_metrics()
    
    def test_edge_cases(self):
        """Test edge cases in the application logic."""
        # Test with price exactly at midpoint
        edge_inputs = self.valid_inputs.copy()
        edge_inputs["price"] = 435.0
        edge_inputs["put_strike"] = 425.0
        edge_inputs["call_strike"] = 445.0
        
        model = OptionsModel(edge_inputs)
        metrics = model.compute_metrics()
        self.assertAlmostEqual(metrics["dist_from_mid"], 0.0)
        
        # Test with very high IV rank
        edge_inputs = self.valid_inputs.copy()
        edge_inputs["iv_rank_pct"] = 95.0
        
        model = OptionsModel(edge_inputs)
        statuses = model.evaluate_status_lights()
        self.assertEqual(statuses["IV Level"], "RED")
        
        # Test with imminent event
        edge_inputs = self.valid_inputs.copy()
        edge_inputs["days_to_event"] = 1
        
        model = OptionsModel(edge_inputs)
        statuses = model.evaluate_status_lights()
        self.assertEqual(statuses["Event Risk"], "RED")


if __name__ == "__main__":
    unittest.main()
