#!/usr/bin/env python3
"""
Run Wave-1 Analysis for 20251001
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analytics.wave1.analyze_wave1_scores import main

if __name__ == "__main__":
    main()
