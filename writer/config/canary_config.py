# file: writer/config/canary_config.py
import os

# Canary configuration
CANARY_ENABLED = os.getenv("BTC_CANARY_ENABLED", "false").lower() == "true"
CANARY_PREFIX = "ticks_canary"
CANARY_WINDOWS = ["20250928/0200-0230"]  # Only affected window


def get_output_prefix(venue: str, date: str, window: str) -> str:
    """Get output prefix, using canary if enabled."""
    base_prefix = f"s3://acd-monitor-snapshots/snapshots/BTC-USD/{date}/{window}/ticks/{venue}"

    if CANARY_ENABLED and f"{date}/{window}" in CANARY_WINDOWS:
        return base_prefix.replace("/ticks/", f"/{CANARY_PREFIX}/")

    return base_prefix
