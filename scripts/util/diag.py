#!/usr/bin/env python3
"""
Diagnostic utilities for monitoring long-running analysis jobs.
"""
import json
import os
import sys
import time
import threading
import traceback
import signal
from datetime import datetime


class Heartbeat:
    """Heartbeat monitor for long-running jobs."""
    
    def __init__(self, path, meta=None):
        self.path = path
        self.state = {
            "ts": None, 
            "rows": 0, 
            "pairs_done": 0, 
            "phase": "init", 
            "meta": meta or {}
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
    
    def tick(self, **kw):
        """Update heartbeat with new state."""
        self.state.update(kw)
        self.state["ts"] = datetime.utcnow().isoformat()
        with open(self.path, "w") as f:
            json.dump(self.state, f, indent=2)


def enable_stackdump(out_path="analysis/_diag/stackdump.txt"):
    """Enable stack dumps on SIGUSR1."""
    import faulthandler
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    f = open(out_path, "w")
    faulthandler.enable(file=f)
    signal.signal(signal.SIGUSR1, lambda s, f2: faulthandler.dump_traceback(file=f))


def watchdog(beat, interval=60):
    """Watchdog thread to keep heartbeat alive."""
    while True:
        beat.tick()  # keep ts fresh
        time.sleep(interval)


def log_progress(beat, phase, rows_done=0, pairs_done=0, **kwargs):
    """Log progress with heartbeat."""
    beat.tick(
        phase=phase,
        rows=int(rows_done),
        pairs_done=int(pairs_done),
        **kwargs
    )
