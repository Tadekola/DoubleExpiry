# DoubleExpiry

An options trading recommender focused on double-expiry calendar strategies, applying mechanical rules to market data for consistent decisions.

## Features

- Analyzes market conditions including price location, volatility measures, and event proximity
- Applies a traffic light system (GREEN/YELLOW/RED) for easy interpretation
- Provides clear trade entry or wait recommendations
- Suggests appropriate strategies based on current market conditions
- Implements guardrails to help manage risk

## Project Structure

```
OptionsApp/
├── .venv/                   # Virtual environment
├── src/
│   ├── components/          # UI components
│   │   └── ui.py            # Streamlit UI elements
│   ├── models/              # Business logic
│   │   └── options_model.py # Core options trading logic
│   ├── utils/               # Utility functions
│   │   └── helpers.py       # Helper functions for calculations and display
│   └── app.py               # Main application logic
├── main.py                  # Entry point for the application
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

## Installation

1. Clone the repository
2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the application with Streamlit:

```
streamlit run main.py
```

## Input Parameters

- **Underlying**: Select from SPY, QQQ, or IWM
- **Price**: Current market price of the underlying
- **Strike Prices**: Short PUT and CALL strikes for the front week
- **Implied Volatility**: Front and back week IV values for PUT and CALL
- **IV Rank**: Current IV rank (0-100%)
- **Days to Event**: Days until a major market event (e.g., FOMC, CPI)
- **VIX**: Current VIX value
- **ATR Guardrail**: Optional Average True Range check

## Development

This project follows best practices for Python development:
- Modular code organization
- Clear separation of concerns
- Proper error handling and input validation
- Comprehensive documentation

## License

Educational purposes only. Not financial advice.
