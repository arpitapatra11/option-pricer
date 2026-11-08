"""Shared option description for the pure-Python reference implementations."""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Option:
    spot: float
    strike: float
    rate: float
    vol: float
    expiry: float
    type: str  # "call" or "put"
    div_yield: float = 0.0
    style: str = "european"  # "european" or "american"

    def __post_init__(self):
        # Comparisons are written so that NaN fails them.
        # Infinity is rejected too: it would otherwise flow through to NaN prices.
        if not (self.spot > 0.0 and math.isfinite(self.spot)):
            raise ValueError("spot must be finite and > 0")
        if not (self.strike > 0.0 and math.isfinite(self.strike)):
            raise ValueError("strike must be finite and > 0")
        if not (self.vol >= 0.0 and math.isfinite(self.vol)):
            raise ValueError("vol must be finite and >= 0")
        if not (self.expiry >= 0.0 and math.isfinite(self.expiry)):
            raise ValueError("expiry must be finite and >= 0")
        if not math.isfinite(self.rate):
            raise ValueError("rate must be finite")
        if not math.isfinite(self.div_yield):
            raise ValueError("div_yield must be finite")
        if self.type not in ("call", "put"):
            raise ValueError("type must be 'call' or 'put'")
        if self.style not in ("european", "american"):
            raise ValueError("style must be 'european' or 'american'")

    @property
    def sign(self) -> int:
        return 1 if self.type == "call" else -1
