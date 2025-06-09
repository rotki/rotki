#!/usr/bin/env python
"""
Simple pytest runner for rotki without gevent.
This replaces the old pytestgeventwrapper.py
"""
import sys
import pytest

if __name__ == '__main__':
    # pytest-asyncio handles async tests automatically
    # No need for gevent monkey patching
    sys.exit(pytest.main(sys.argv[1:]))