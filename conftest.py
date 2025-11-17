"""
Pytest Configuration

Sets up Python path and test environment for ONYX project.
"""

import sys
import os

# Add onyx-core to Python path so tests can import services and utils
onyx_core_path = os.path.join(os.path.dirname(__file__), "onyx-core")
if onyx_core_path not in sys.path:
    sys.path.insert(0, onyx_core_path)

# Add project root for additional imports
project_root = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
