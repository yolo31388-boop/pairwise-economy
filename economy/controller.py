"""经济系统调控"""
import time
from dataclasses import dataclass, field

# 货币总量上限
TOTAL_CURRENCY_CAP = 10_000_000
# 发行速率限制:单来源每个时间窗内的最大发行量
ISSUE_WINDOW_SECONDS = 3600
ISSUE_WINDOW_LIMIT = 500_000
# 回收场景:商城购买之外,覆盖修理/传送/强化/税收
SINK_SCENARIOS = {"shop", "repair", "teleport", "enhance", "tax"}
# 累进税率档位:(上限, 税率),按边际税率计算
TAX_BRACKETS = [(1_000, 0.05), (100_000, 0.10), (float("inf"), 0.20)]
# 通胀指数的一篮子商品基准价
BASE_BASKET = {
    "sword": 100,
    "shield": 150,
    "potion": 30,
    "armor": 200,
    "bread": 5,
}


@dataclass
class EconomyState:
    total_currency: int = 0
    inflation_index: float = 1.0
    prices: dict = field(default_factory=dict)


class EconomyController:
    def __init__(self):
        self.state = EconomyState()
        self.issued: dict[str, int] = {}
        self._issue_windows: dict[str, tuple[float, int]] = {}

    def issue_currency(self, source: str, amount: int) -> bool:
        if amount <= 0:
            return False
        # 总量上限
        if self.state.total_currency + amount > TOTAL_CURRENCY_CAP:
            return False
        # 发行速率限制
        now = time.monotonic()
        window_start, window_issued = self._issue_windows.get(source, (now, 0))
        if now - window_start >= ISSUE_WINDOW_SECONDS:
            window_start, window_issued = now, 0
        if window_issued + amount > ISSUE_WINDOW_LIMIT:
            return False
        self._issue_windows[source] = (window_start, window_issued + amount)
        self.state.total_currency += amount
        self.issued[source] = self.issued.get(source, 0) + amount
        return True

    def sink_currency(self, amount: int, reason: str = "shop") -> bool:
        # 回收覆盖多种场景
        if reason not in SINK_SCENARIOS:
            return False
        if amount <= 0:
            return False
        if self.state.total_currency >= amount:
            self.state.total_currency -= amount
            return True
        return False

    def calculate_tax(self, amount: int) -> int:
        # 累进税率,按档位边际计算
        tax = 0.0
        lower = 0
        for upper, rate in TAX_BRACKETS:
            if amount <= lower:
                break
            taxable = min(amount, upper) - lower
            tax += taxable * rate
            lower = upper
        return int(tax)

    def calculate_inflation_index(self, goods_prices: dict) -> float:
        # 按一篮子商品加权计算
        ratios = [
            goods_prices[good] / base
            for good, base in BASE_BASKET.items()
            if good in goods_prices and base > 0
        ]
        if not ratios:
            return 1.0
        return sum(ratios) / len(ratios)

    def sync_cross_server(self, remote_state: EconomyState, rate: float) -> EconomyState:
        # 跨服同步按汇率转换
        return EconomyState(
            total_currency=int(remote_state.total_currency * rate),
            inflation_index=remote_state.inflation_index,
            prices={k: v * rate for k, v in remote_state.prices.items()},
        )
