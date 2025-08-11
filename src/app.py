"""
Mechanical Options Trade Recommender

A Streamlit application that provides rule-based recommendations for options trading.
This application applies mechanical rules to market data to assist traders in making
consistent decisions while removing emotional bias.

Author: Options Trading Team
Version: 2.0.0
Last Updated: 2025-08-10
"""

import logging
import traceback
import streamlit as st

from src.components.ui import setup_page, render_sidebar, render_metrics, render_status_lights, render_decision, render_suggestions
from src.models.options_model import OptionsModel
from src.utils.validation import ValidationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point.
    
    Sets up the Streamlit page, processes user inputs, and displays results.
    Includes error handling for validation errors and unexpected exceptions.
    """
    # Set up page configuration
    setup_page()
    
    try:
        # Render the sidebar and get user inputs
        logger.info("Rendering sidebar and collecting user inputs")
        inputs = render_sidebar()
        
        # Create model instance and compute metrics
        logger.info("Creating model instance and processing inputs")
        model = OptionsModel(inputs)
        
        try:
            # Compute metrics and evaluate status
            metrics = model.compute_metrics()
            statuses = model.evaluate_status_lights()
            
            # Display results
            logger.info("Rendering results to the user interface")
            render_metrics(metrics)
            render_status_lights(statuses)
            decision = model.get_final_decision()
            render_decision(decision)
            suggestions = model.get_strategy_suggestions()
            render_suggestions(suggestions)
            
            # Add disclaimer
            st.caption("Educational tool only. Not financial advice.")
            
            logger.info("Application execution completed successfully")
            
        except ValidationError as e:
            # Handle validation errors gracefully
            st.error(f"⚠️ Input validation error: {str(e)}")
            st.warning("Please correct the input values and try again.")
            logger.warning(f"Validation error: {str(e)}")
            
    except Exception as e:
        # Catch any unexpected errors
        st.error("⚠️ An unexpected error occurred")
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
