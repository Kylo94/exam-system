"""
Pytest configuration file for the exam system tests.
This file ensures proper Python path setup and provides shared fixtures.
"""

import sys
import os

# Add the project root to Python path to allow importing app modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)