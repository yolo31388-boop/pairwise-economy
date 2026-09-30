"""经济系统调控 - 含5个bug"""
from dataclasses import dataclass, field

@dataclass
class EconomyState:
    total_currency: int = 0
    inflation_index: float = 1.0
    prices: dict = field(default_factory=dict)

class EconomyController:
    def __init__(self):
        self.state = EconomyState()
        self.issued: dict[str, int] = {}

    def issue_currency(self, source: str, amount: int) -> bool:
        # bug1: 无总量上限
        self.state.total_currency += amount
        self.issued[source] = self.issued.get(source, 0) + amount
        return True

    def sink_currency(self, amount: int) -> bool:
        # bug2: 回收场景单一
        if self.state.total_currency >= amount:
            self.state.total_currency -= amount
            return True
        return False

    def calculate_tax(self, amount: int) -> int:
        # bug3: 固定税率无累进
        return int(amount * 0.05)

    def calculate_inflation_index(self, goods_prices: dict) -> float:
        # bug4: 只看少数商品
        if "sword" in goods_prices:
            return goods_prices["sword"] / 100.0
        return 1.0

    def sync_cross_server(self, remote_state: EconomyState, rate: float) -> EconomyState:
        # bug5: 无汇率转换
        return remote_state
