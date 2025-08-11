"""
IBKRClient helper for fetching market data via ib_insync.

- Connects to TWS/Gateway using ib_insync
- Fetches underlying last price (real-time if permissioned, else delayed via reqMarketDataType(3))
- Computes nearest two Friday expirations
- Retrieves option model Greeks/IV (generic tick 106) for specified strikes and expirations
- Attempts to fetch VIX via IBKR; falls back to yfinance if unavailable
"""
from __future__ import annotations

import datetime as dt
import logging
import math
from typing import Dict, Optional, Tuple

try:
    from ib_insync import IB, Stock, Option, Index  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    IB = None  # type: ignore
    Stock = Option = Index = None  # type: ignore

try:
    import yfinance as yf  # type: ignore
except Exception:  # pragma: no cover
    yf = None  # type: ignore

logger = logging.getLogger(__name__)


class IBKRClient:
    """Thin convenience wrapper around ib_insync for this app's needs."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        delayed: bool = True,
        connect_timeout_s: float = 5.0,
    ) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.delayed = delayed
        self.connect_timeout_s = connect_timeout_s
        self.ib: Optional[IB] = None

    def ensure_connected(self) -> bool:
        if IB is None:
            # Attempt lazy import in case package was installed after module load
            try:
                import importlib, sys, asyncio
                importlib.invalidate_caches()
                # Ensure an event loop exists for this thread (Streamlit worker threads may lack one)
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    asyncio.set_event_loop(asyncio.new_event_loop())
                _mod = importlib.import_module("ib_insync")  # type: ignore
                globals()["IB"] = getattr(_mod, "IB")
                globals()["Stock"] = getattr(_mod, "Stock")
                globals()["Option"] = getattr(_mod, "Option")
                globals()["Index"] = getattr(_mod, "Index")
            except Exception as e:  # still unavailable
                import sys
                logger.warning(
                    "ib_insync import failed; IBKR connectivity disabled (python=%s, error=%s)", sys.executable, repr(e)
                )
                return False
        if self.ib and self.ib.isConnected():
            return True
        # At this point IB class is available. Make sure event loop exists before creating IB()
        try:
            import asyncio
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())
        except Exception:
            pass
        self.ib = IB()
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id, timeout=self.connect_timeout_s)
            # 1 = real-time, 3 = delayed, 4 = delayed-frozen
            if self.delayed:
                self.ib.reqMarketDataType(3)
            else:
                self.ib.reqMarketDataType(1)
            logger.info("Connected to IBKR TWS/Gateway at %s:%s", self.host, self.port)
            return True
        except Exception as e:  # pragma: no cover - runtime connectivity
            logger.warning("Could not connect to IBKR: %s", e)
            return False

    def get_underlying_price(self, symbol: str) -> Optional[float]:
        if not self.ensure_connected():
            return None

    def get_iv_rank(self, symbol: str, target_days: int = 30, lookback_days: int = 252) -> Optional[float]:
        """Compute IV Rank over lookback_days for approximately target_days-to-expiry ATM option.

        Attempts using IBKR OPTION_IMPLIED_VOLATILITY daily bars. Falls back to VIX percentile via yfinance.
        Returns IV Rank as percentage (0-100) or None if unavailable.
        """
        try:
            # First try IBKR option IV history
            if self.ensure_connected() and Option is not None:
                # Qualify underlying and discover valid expirations/strikes
                stk = Stock(symbol, "SMART", "USD")
                self.ib.qualifyContracts(stk)
                # Fetch ATM price if possible
                px = self.get_underlying_price(symbol)
                # Discover option parameters
                params = self.ib.reqSecDefOptParams(symbol, "", "STK", stk.conId)
                if not params:
                    raise RuntimeError("No option parameters returned")
                p = params[0]
                # Choose expiry closest to target_days
                today = dt.date.today()
                exp_dates = sorted([
                    dt.datetime.strptime(e, "%Y%m%d").date() for e in p.expirations
                    if len(e) == 8
                ])
                if not exp_dates:
                    raise RuntimeError("No expirations available")
                target_date = today + dt.timedelta(days=target_days)
                expiry = min(exp_dates, key=lambda d: abs((d - target_date).days))
                # Choose strike candidates nearest to px; if px unknown, use middle of list
                strikes = sorted([float(s) for s in p.strikes if math.isfinite(float(s))])
                if not strikes:
                    raise RuntimeError("No strikes available")
                if px is None or not math.isfinite(px):
                    px = strikes[len(strikes)//2]
                # create an ordered list of nearest strikes
                candidates = sorted(strikes, key=lambda s: abs(s - px))[:8]
                # choose an exchange; OptionChain exposes `exchange`, not `exchanges`
                exch = getattr(p, "exchange", None) or "SMART"

                # find a valid contract via contract details
                valid_contract = None
                for s in candidates:
                    for right in ("C", "P"):
                        try:
                            probe = Option(symbol, expiry.strftime("%Y%m%d"), float(s), right, exch)
                            cds = self.ib.reqContractDetails(probe)
                            if cds:
                                valid_contract = cds[0].contract
                                break
                        except Exception:
                            continue
                    if valid_contract:
                        break

                if not valid_contract:
                    raise RuntimeError("No valid option contract found near ATM")

                bars = self.ib.reqHistoricalData(
                    valid_contract,
                    endDateTime="",
                    durationStr=f"{lookback_days} D",
                    barSizeSetting="1 day",
                    whatToShow="OPTION_IMPLIED_VOLATILITY",
                    useRTH=False,
                    keepUpToDate=False,
                )
                series = [b.close for b in bars if b.close is not None and math.isfinite(b.close)]
                if len(series) >= 5:
                    cur = series[-1]
                    lo = min(series)
                    hi = max(series)
                    if hi > lo:
                        rank = (cur - lo) / (hi - lo) * 100.0
                        # clip to [0,100]
                        rank = max(0.0, min(100.0, float(rank)))
                        logger.info("Computed IV Rank from IBKR for %s: %.2f%% (cur=%.4f lo=%.4f hi=%.4f)", symbol, rank, cur, lo, hi)
                        return rank
        except Exception as e:
            logger.warning("IBKR IV Rank fetch failed for %s: %s", symbol, e)

        # Fallback: VIX percentile via yfinance
        try:
            if yf is None:
                return None
            data = yf.Ticker("^VIX").history(period=f"{lookback_days}d")
            if not data.empty:
                s = data["Close"].dropna()
                if not s.empty:
                    cur = float(s.iloc[-1])
                    lo = float(s.min())
                    hi = float(s.max())
                    if hi > lo:
                        rank = (cur - lo) / (hi - lo) * 100.0
                        rank = max(0.0, min(100.0, float(rank)))
                        logger.info("Computed IV Rank proxy from VIX: %.2f%% (cur=%.4f lo=%.4f hi=%.4f)", rank, cur, lo, hi)
                        return rank
        except Exception as e:
            logger.warning("VIX proxy IV Rank failed: %s", e)
        return None
        contract = Stock(symbol, "SMART", "USD")
        self.ib.qualifyContracts(contract)
        ticker = self.ib.reqMktData(contract, "", False, False)
        self.ib.sleep(1.5)
        last = ticker.last
        mid = None
        if ticker.bid is not None and ticker.ask is not None and ticker.ask > 0:
            mid = (ticker.bid + ticker.ask) / 2.0
        close = ticker.close
        price = last or mid or close
        # If price is None or NaN, attempt fallbacks
        def _is_valid(x: Optional[float]) -> bool:
            return x is not None and isinstance(x, (int, float)) and math.isfinite(float(x))

        if not _is_valid(price):
            # Try switching to delayed/frozen if not already
            try:
                self.ib.reqMarketDataType(3)  # delayed
                t2 = self.ib.reqMktData(contract, "", False, False)
                self.ib.sleep(1.5)
                price2 = t2.last or ((t2.bid + t2.ask) / 2.0 if t2.bid and t2.ask and t2.ask > 0 else None) or t2.close
                if _is_valid(price2):
                    price = price2
            except Exception:
                pass

        if not _is_valid(price):
            # Fallback to historical close via IBKR
            try:
                bars = self.ib.reqHistoricalData(
                    contract,
                    endDateTime="",
                    durationStr="1 D",
                    barSizeSetting="1 day",
                    whatToShow="TRADES",
                    useRTH=False,
                    keepUpToDate=False,
                )
                if bars:
                    price = float(bars[-1].close)
            except Exception:
                pass

        if not _is_valid(price) and yf is not None:
            # Final fallback to yfinance
            try:
                data = yf.Ticker(symbol).history(period="1d")
                if not data.empty:
                    price = float(data["Close"].iloc[-1])
            except Exception:
                pass

        logger.info("Fetched underlying price for %s: %s (last=%s mid=%s close=%s)", symbol, price, last, mid, close)
        return float(price) if _is_valid(price) else None

    @staticmethod
    def nearest_two_fridays(from_date: Optional[dt.date] = None) -> Tuple[dt.date, dt.date]:
        d = from_date or dt.date.today()
        # find next Friday (weekday 4)
        days_ahead = (4 - d.weekday()) % 7
        if days_ahead == 0:
            first = d
        else:
            first = d + dt.timedelta(days=days_ahead)
        second = first + dt.timedelta(days=7)
        return first, second

    def get_option_ivs(
        self, symbol: str, expiry_front: dt.date, expiry_back: dt.date, put_strike: float, call_strike: float
    ) -> Dict[str, Optional[float]]:
        """Fetch model IVs for front and back week for PUT and CALL at given strikes.
        Returns keys: front_put_iv, front_call_iv, back_put_iv, back_call_iv
        """
        if not self.ensure_connected():
            return {k: None for k in ["front_put_iv", "front_call_iv", "back_put_iv", "back_call_iv"]}

        def _iv(expiry: dt.date, right: str, strike: float) -> Optional[float]:
            opt = Option(symbol, expiry.strftime("%Y%m%d"), strike, right, "SMART")
            self.ib.qualifyContracts(opt)
            # generic tick 106 to force model greeks/IV
            ticker = self.ib.reqMktData(opt, genericTickList="106", snapshot=False, regulatorySnapshot=False)
            self.ib.sleep(1.5)
            g = getattr(ticker, "modelGreeks", None)
            iv = getattr(g, "impliedVol", None) if g else None
            # convert to percent if returned as decimal
            if iv is not None and iv < 1.0:
                iv = iv * 100.0
            return float(iv) if iv is not None else None

        result = {
            "front_put_iv": _iv(expiry_front, "P", put_strike),
            "front_call_iv": _iv(expiry_front, "C", call_strike),
            "back_put_iv": _iv(expiry_back, "P", put_strike),
            "back_call_iv": _iv(expiry_back, "C", call_strike),
        }
        logger.info("Fetched IVs: %s", result)
        return result

    def get_vix(self) -> Optional[float]:
        # Try IBKR
        if self.ensure_connected() and Index is not None:
            try:
                vix = Index("VIX", "CBOE")
                self.ib.qualifyContracts(vix)
                t = self.ib.reqMktData(vix, "", False, False)
                self.ib.sleep(1.0)
                price = t.last or t.close
                if price:
                    return float(price)
            except Exception as e:
                logger.warning("IBKR VIX fetch failed: %s", e)
        # Fallback to yfinance
        try:
            if yf is None:
                return None
            data = yf.Ticker("^VIX").history(period="1d")
            if not data.empty:
                return float(data["Close"].iloc[-1])
        except Exception as e:
            logger.warning("yfinance VIX fetch failed: %s", e)
        return None
