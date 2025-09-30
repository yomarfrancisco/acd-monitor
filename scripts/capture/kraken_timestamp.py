#!/usr/bin/env python3
"""
Kraken Timestamp Normalizer
Handles various Kraken timestamp formats with robust parsing
"""

import re
import pandas as pd
import numpy as np
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


class KrakenTimestamp:
    """Robust Kraken timestamp parser with multiple format support."""

    @staticmethod
    def normalize(ts: Union[str, int, float]) -> Optional[pd.Timestamp]:
        """
        Normalize various Kraken timestamp formats to pandas Timestamp.

        Handles:
        - int/float seconds: 1695758400
        - string with digits: "1695758400.123456"
        - string with stray letters: "s1695758400", "1695758400s", "t=1695758400"
        - ISO8601: "2023-09-26T10:00:00Z"
        """
        if ts is None:
            return None

        try:
            # Case 1: Already numeric (int/float)
            if isinstance(ts, (int, float)):
                if np.isnan(ts) or ts == 0:
                    return None
                return pd.to_datetime(ts, unit="s", utc=True)

            # Case 2: String - try to extract numeric part
            if isinstance(ts, str):
                ts_str = str(ts).strip()

                # Case 2a: ISO8601 format (contains T or Z)
                if "T" in ts_str or "Z" in ts_str:
                    return pd.to_datetime(ts_str, utc=True)

                # Case 2b: Extract numeric part from string with letters
                # Pattern: extract digits and optional decimal point
                numeric_match = re.search(r"(\d+(?:\.\d+)?)", ts_str)
                if numeric_match:
                    numeric_value = float(numeric_match.group(1))
                    return pd.to_datetime(numeric_value, unit="s", utc=True)

                # Case 2c: Try direct string conversion
                try:
                    numeric_value = float(ts_str)
                    return pd.to_datetime(numeric_value, unit="s", utc=True)
                except ValueError:
                    pass

            # If all parsing attempts fail
            logger.warning(f"[KRAKEN:TS_PARSE_FAIL] raw={str(ts)[:50]}...")
            return None

        except Exception as e:
            logger.warning(f"[KRAKEN:TS_PARSE_FAIL] raw={str(ts)[:50]}... error={e}")
            return None

    @staticmethod
    def is_enabled() -> bool:
        """Check if Kraken timestamp flexibility is enabled."""
        import os

        return os.getenv("KRAKEN_TS_FLEX", "1").lower() in ("1", "true", "on", "yes")


def test_kraken_timestamp():
    """Test the Kraken timestamp normalizer with various formats."""
    test_cases = [
        # Numeric formats
        (1695758400, "int seconds"),
        (1695758400.123, "float seconds"),
        # String formats
        ("1695758400", "string seconds"),
        ("1695758400.123456", "string with decimal"),
        ("s1695758400", "string with prefix"),
        ("1695758400s", "string with suffix"),
        ("t=1695758400", "string with prefix and equals"),
        ("2023-09-26T10:00:00Z", "ISO8601"),
        # Edge cases
        (None, "None"),
        ("", "empty string"),
        ("invalid", "invalid string"),
        (0, "zero"),
    ]

    print("Testing Kraken Timestamp Normalizer:")
    print("=" * 50)

    for test_input, description in test_cases:
        result = KrakenTimestamp.normalize(test_input)
        status = "✅" if result is not None else "❌"
        print(f"{status} {description:20} | {test_input} → {result}")

    print("=" * 50)


if __name__ == "__main__":
    test_kraken_timestamp()
