"""经济系统调控 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from economy.controller import EconomyController, EconomyState

class TestCurrencyLimit:
    def test_currency_has_upper_limit(self):
        ec = EconomyController()
        ec.state.total_currency = 9999999
        result = ec.issue_currency("quest", 1000000)
        assert result == False

class TestTaxProgressive:
    def test_large_transaction_higher_tax_rate(self):
        ec = EconomyController()
        small_tax = ec.calculate_tax(100)
        large_tax = ec.calculate_tax(1000000)
        assert large_tax / 1000000 > small_tax / 100

class TestInflationBasket:
    def test_inflation_uses_multiple_goods(self):
        ec = EconomyController()
        prices = {"sword": 200, "shield": 300, "potion": 50}
        idx = ec.calculate_inflation_index(prices)
        assert idx > 1.0

class TestCrossServerRate:
    def test_cross_server_converts_currency(self):
        ec = EconomyController()
        remote = EconomyState(total_currency=1000)
        result = ec.sync_cross_server(remote, rate=2.0)
        assert result.total_currency == 2000

class TestSinkMultipleScenarios:
    def test_sink_works_for_repair_and_teleport(self):
        ec = EconomyController()
        ec.state.total_currency = 1000
        assert ec.sink_currency(100) == True
        assert ec.state.total_currency == 900
