#!/usr/bin/env python3
"""
Run Variance Ratio Diagnostic Analysis
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analytics.wave1.diagnose_variance_ratios import main

if __name__ == "__main__":
    main()
