"""
Tests for the validation module.
"""
import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.validation import validate_positive, validate_range, validate_strikes, ValidationError

class TestValidation(unittest.TestCase):
    """Test cases for validation functions."""
    
    def test_validate_positive(self):
        """Test the validate_positive function."""
        # Valid cases
        self.assertEqual(validate_positive(1, "test"), 1)
        self.assertEqual(validate_positive(100.5, "test"), 100.5)
        
        # Invalid cases
        with self.assertRaises(ValidationError):
            validate_positive(0, "test")
        with self.assertRaises(ValidationError):
            validate_positive(-5, "test")
    
    def test_validate_range(self):
        """Test the validate_range function."""
        # Valid cases - within range
        self.assertEqual(validate_range(5, "test", min_val=1, max_val=10), 5)
        self.assertEqual(validate_range(1, "test", min_val=1, max_val=10), 1)  # Edge case - min
        self.assertEqual(validate_range(10, "test", min_val=1, max_val=10), 10)  # Edge case - max
        
        # Invalid cases - outside range
        with self.assertRaises(ValidationError):
            validate_range(0, "test", min_val=1, max_val=10)
        with self.assertRaises(ValidationError):
            validate_range(11, "test", min_val=1, max_val=10)
        
        # Test with only min_val
        self.assertEqual(validate_range(5, "test", min_val=1), 5)
        with self.assertRaises(ValidationError):
            validate_range(0, "test", min_val=1)
        
        # Test with only max_val
        self.assertEqual(validate_range(5, "test", max_val=10), 5)
        with self.assertRaises(ValidationError):
            validate_range(11, "test", max_val=10)
    
    def test_validate_strikes(self):
        """Test the validate_strikes function."""
        # Valid case - put strike less than call strike
        self.assertTrue(validate_strikes(100, 110))
        
        # Invalid cases
        with self.assertRaises(ValidationError):
            validate_strikes(100, 100)  # Equal strikes
        with self.assertRaises(ValidationError):
            validate_strikes(110, 100)  # Put strike greater than call strike

if __name__ == '__main__':
    unittest.main()
