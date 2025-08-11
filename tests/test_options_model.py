"""
Tests for the OptionsModel class.
"""
import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.options_model import OptionsModel
from src.utils.validation import ValidationError

class TestOptionsModel(unittest.TestCase):
    """Test cases for the OptionsModel class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Valid test inputs for model initialization
        self.valid_inputs = {
            'symbol': 'SPY',
            'price': 435.0,
            'put_strike': 425.0,
            'call_strike': 445.0,
            'front_put_iv': 22.0,
            'front_call_iv': 20.0,
            'back_put_iv': 18.0,
            'back_call_iv': 19.0,
            'iv_rank_pct': 45.0,
            'days_to_event': 5,
            'vix_value': 18.0,
            'atr_points': 4.0,
            'use_atr': True
        }
        
        # Invalid test inputs
        self.invalid_price_inputs = self.valid_inputs.copy()
        self.invalid_price_inputs['price'] = 0
        
        self.invalid_strikes_inputs = self.valid_inputs.copy()
        self.invalid_strikes_inputs['put_strike'] = 450.0  # Put strike > call strike
        self.invalid_strikes_inputs['call_strike'] = 430.0
    
    def test_model_initialization(self):
        """Test model initialization with valid inputs."""
        model = OptionsModel(self.valid_inputs)
        self.assertEqual(model.inputs, self.valid_inputs)
        self.assertEqual(model.metrics, {})
        self.assertEqual(model.statuses, {})
    
    def test_model_validation(self):
        """Test input validation during model initialization."""
        # Valid inputs should not raise exceptions
        try:
            OptionsModel(self.valid_inputs)
        except ValidationError:
            self.fail("OptionsModel raised ValidationError unexpectedly with valid inputs")
        
        # Invalid price should raise ValidationError
        with self.assertRaises(ValidationError):
            OptionsModel(self.invalid_price_inputs)
        
        # Invalid strikes should raise ValidationError
        with self.assertRaises(ValidationError):
            OptionsModel(self.invalid_strikes_inputs)
    
    def test_compute_metrics(self):
        """Test the computation of metrics."""
        model = OptionsModel(self.valid_inputs)
        metrics = model.compute_metrics()
        
        # Check that all expected metrics are present
        expected_metrics = [
            'midpoint', 'dist_from_mid', 'strike_width', 
            'front_avg_iv', 'back_avg_iv', 'term_gap_pts',
            'iv_rank', 'atr_ok', 'use_atr', 'atr_points'
        ]
        for metric in expected_metrics:
            self.assertIn(metric, metrics)
        
        # Check specific calculations
        self.assertEqual(metrics['midpoint'], (425.0 + 445.0) / 2)  # (put_strike + call_strike) / 2
        self.assertEqual(metrics['strike_width'], 20.0)  # call_strike - put_strike
        self.assertEqual(metrics['front_avg_iv'], 21.0)  # (front_put_iv + front_call_iv) / 2
        self.assertEqual(metrics['back_avg_iv'], 18.5)  # (back_put_iv + back_call_iv) / 2
        self.assertEqual(metrics['term_gap_pts'], 2.5)  # front_avg_iv - back_avg_iv
    
    def test_status_lights(self):
        """Test the evaluation of status lights."""
        model = OptionsModel(self.valid_inputs)
        model.compute_metrics()
        statuses = model.evaluate_status_lights()
        
        # Check that all expected statuses are present
        expected_statuses = [
            'Price Location', 'Term Structure', 'IV Rank', 
            'Event Proximity', 'VIX'
        ]
        for status in expected_statuses:
            self.assertIn(status, statuses)
        
        # Since we're using ATR, that status should also be present
        self.assertIn('ATR Guardrail', statuses)
        
        # Check that all statuses have valid values
        for value in statuses.values():
            self.assertIn(value, ['GREEN', 'YELLOW', 'RED'])
    
    def test_final_decision(self):
        """Test the final decision logic."""
        model = OptionsModel(self.valid_inputs)
        model.compute_metrics()
        model.evaluate_status_lights()
        decision = model.get_final_decision()
        
        # Decision should be one of the expected strings
        possible_decisions = [
            "ENTER (All green) ✅", 
            "ENTER — CAUTION ⚠️", 
            "WAIT ❌"
        ]
        self.assertIn(decision, possible_decisions)
    
    def test_strategy_suggestions(self):
        """Test the strategy suggestion logic."""
        model = OptionsModel(self.valid_inputs)
        model.compute_metrics()
        model.evaluate_status_lights()
        suggestions = model.get_strategy_suggestions()
        
        # Result should be a non-empty list
        self.assertIsInstance(suggestions, list)
        self.assertTrue(len(suggestions) > 0)
        
        # Each suggestion should be a string
        for suggestion in suggestions:
            self.assertIsInstance(suggestion, str)

if __name__ == '__main__':
    unittest.main()
