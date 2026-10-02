"""经济系统调控

修复内容:
1. 货币发行有总量上限 + 分渠道发行速率限制
2. 货币回收覆盖商城/修理/传送/强化/税收等多种场景
3. 交易税实行超额累进税率
4. 通货膨胀指数按一篮子商品加权计算
5. 跨服经济数据按汇率转换
"""
from dataclasses import dataclass, field
import time


@dataclass
class EconomyState:
    total_currency: int = 0
    inflation_index: float = 1.0
    prices: dict = field(default_factory=dict)


class EconomyController:
    # 货币总量上限 (M2 cap)
    MAX_TOTAL_CURRENCY = 10_000_000
    # 单个发行渠道在一个时间窗口内的最大发行量
    ISSUE_RATE_LIMIT = 10_000_000
    ISSUE_RATE_WINDOW = 60.0  # seconds

    # 回收场景
    SINK_SCENES = ("mall", "repair", "teleport", "enhance", "tax")

    # 超额累进税率表: (区间下限, 区间上限, 税率)
    TAX_BRACKETS = (
        (0, 10_000, 0.05),
        (10_000, 100_000, 0.10),
        (100_000, 1_000_000, 0.20),
        (1_000_000, float("inf"), 0.30),
    )

    # 通胀计算用的一篮子基准商品 (基期价格均为 100)
    BASELINE_PRICES = {
        "sword": 100.0,
        "shield": 100.0,
        "potion": 100.0,
        "armor": 100.0,
        "helmet": 100.0,
        "bow": 100.0,
        "staff": 100.0,
        "ring": 100.0,
        "gem": 100.0,
        "food": 100.0,
    }
    BASKET_WEIGHTS = {name: 1.0 for name in BASELINE_PRICES}

    def __init__(
        self,
        max_total_currency: int | None = None,
        issue_rate_limit: int | None = None,
        rate_window: float | None = None,
    ):
        self.state = EconomyState()
        self.issued: dict[str, int] = {}
        self.sunk: dict[str, int] = {scene: 0 for scene in self.SINK_SCENES}
        self.max_total_currency = (
            self.MAX_TOTAL_CURRENCY if max_total_currency is None else max_total_currency
        )
        self.issue_rate_limit = (
            self.ISSUE_RATE_LIMIT if issue_rate_limit is None else issue_rate_limit
        )
        self.rate_window = self.ISSUE_RATE_WINDOW if rate_window is None else rate_window
        # source -> [(timestamp, amount), ...] 滑动窗口发行记录
        self._issue_window: dict[str, list[tuple[float, int]]] = {}

    def issue_currency(self, source: str, amount: int) -> bool:
        """发行货币, 受总量上限与分渠道速率限制约束。"""
        if amount <= 0:
            return False

        # 总量上限
        if self.state.total_currency + amount > self.max_total_currency:
            return False

        now = time.monotonic()
        records = self._issue_window.setdefault(source, [])
        cutoff = now - self.rate_window
        records[:] = [item for item in records if item[0] > cutoff]

        # 发行速率限制 (滑动窗口)
        window_total = sum(item[1] for item in records)
        if window_total + amount > self.issue_rate_limit:
            return False

        records.append((now, amount))
        self.state.total_currency += amount
        self.issued[source] = self.issued.get(source, 0) + amount
        return True

    def sink_currency(self, amount: int, scene: str = "mall") -> bool:
        """回收货币, 支持修理/传送/强化/税收等多种回收场景。"""
        if amount <= 0 or scene not in self.SINK_SCENES:
            return False
        if self.state.total_currency < amount:
            return False
        self.state.total_currency -= amount
        self.sunk[scene] += amount
        return True

    # 语义别名
    def sink_gold(self, amount: int, scene: str = "mall") -> bool:
        return self.sink_currency(amount, scene)

    def calculate_tax(self, amount: int) -> int:
        """按超额累进税率计算交易税。"""
        if amount <= 0:
            return 0
        tax = 0
        remaining = amount
        for lower, upper, rate in self.TAX_BRACKETS:
            if amount <= lower:
                break
            taxable = min(remaining, upper - lower)
            tax += taxable * rate
            remaining -= taxable
        return int(tax)

    def calculate_inflation_index(self, goods_prices: dict) -> float:
        """按一篮子商品的现价/基期价格加权平均计算通胀指数。"""
        weighted_ratio = 0.0
        total_weight = 0.0
        for name, price in goods_prices.items():
            baseline = self.BASELINE_PRICES.get(name)
            if baseline is None or baseline <= 0:
                continue
            weight = self.BASKET_WEIGHTS.get(name, 1.0)
            weighted_ratio += (price / baseline) * weight
            total_weight += weight

        if total_weight == 0:
            index = 1.0
        else:
            index = weighted_ratio / total_weight

        self.state.inflation_index = index
        self.state.prices = dict(goods_prices)
        return index

    def sync_cross_server(self, remote_state: EconomyState, rate: float) -> EconomyState:
        """按汇率把远端服经济数据转换为本服口径后返回 (不修改入参)。"""
        if rate <= 0:
            raise ValueError("汇率必须为正数")
        converted = EconomyState(
            total_currency=int(round(remote_state.total_currency * rate)),
            inflation_index=remote_state.inflation_index,
            prices={name: price * rate for name, price in remote_state.prices.items()},
        )
        return converted

    # 语义别名
    def sync_economy_data(self, remote_state: EconomyState, rate: float) -> EconomyState:
        return self.sync_cross_server(remote_state, rate)
