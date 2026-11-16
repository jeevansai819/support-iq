"""
SupportIQ — Unit Tests
Run with: venv\Scripts\python.exe -m pytest tests\ -v
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Allow importing from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ==========================================
# PRIORITY CLASSIFIER TESTS
# ==========================================

from backend.main import classify_priority


class TestClassifyPriority:

    def test_fraud_is_high(self):
        assert classify_priority("My account was hit by fraud") == "High"

    def test_hacked_is_high(self):
        assert classify_priority("I think my account has been hacked") == "High"

    def test_urgent_is_high(self):
        assert classify_priority("This is urgent please help") == "High"

    def test_payment_failed_is_high(self):
        assert classify_priority("My payment failed") == "High"

    def test_money_deducted_is_high(self):
        assert classify_priority("Money was deducted but order not placed") == "High"

    def test_double_payment_is_high(self):
        assert classify_priority("I was charged a double payment") == "High"

    def test_refund_is_medium(self):
        assert classify_priority("I want a refund for my order") == "Medium"

    def test_delivery_delay_is_medium(self):
        assert classify_priority("My order has a delivery delay") == "Medium"

    def test_late_delivery_is_medium(self):
        assert classify_priority("The late delivery is unacceptable") == "Medium"

    def test_cancel_order_is_medium(self):
        assert classify_priority("I need to cancel order 12345") == "Medium"

    def test_general_query_is_low(self):
        assert classify_priority("I have a general question about my account") == "Low"

    def test_empty_string_is_low(self):
        assert classify_priority("") == "Low"

    def test_case_insensitive(self):
        assert classify_priority("FRAUD DETECTED") == "High"
        assert classify_priority("REFUND PLEASE") == "Medium"

    def test_high_takes_priority_over_medium(self):
        # Both "refund" and "urgent" present — High should win
        assert classify_priority("urgent refund needed") == "High"
