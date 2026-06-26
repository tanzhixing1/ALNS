"""
CVRP ALNS 小规模学习脚本。

这个脚本来自 examples/capacitated_vehicle_routing_problem.ipynb 的核心逻辑，
但只保留前 NUM_CUSTOMERS 个客户，方便在 PyCharm 中单步调试。
"""

from __future__ import annotations

import copy
import sys
import time
from pathlib import Path

import numpy as np
import numpy.random as rnd
import vrplib


# 让 PyCharm 直接运行本文件时，也能 import 本地 alns 包。
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alns import ALNS  # noqa: E402
from alns.accept import RecordToRecordTravel  # noqa: E402
from alns.select import RouletteWheel  # noqa: E402
from alns.stop import MaxIterations  # noqa: E402


# 学习用小规模参数。
NUM_CUSTOMERS = 20
NUM_ITERATIONS = 500
RANDOM_SEED = 1234

DATA_DIR = ROOT / "examples" / "data"


def load_small_cvrp_data():
    """
    读取原始 241 客户 CVRP 数据，但只保留：
    - depot 节点 0；
    - 前 NUM_CUSTOMERS 个客户，也就是 1..NUM_CUSTOMERS。

    同步裁剪 edge_weight、demand、node_coord 等按节点存储的数据。
    """
    raw_data = vrplib.read_instance(str(DATA_DIR / "ORTEC-n242-k12.vrp"))
    original_dimension = raw_data["dimension"]
    selected = np.arange(NUM_CUSTOMERS + 1)

    small_data = {}
    for key, value in raw_data.items():
        if key == "dimension":
            small_data[key] = NUM_CUSTOMERS + 1
            continue

        if isinstance(value, np.ndarray):
            if value.ndim == 2 and value.shape[:2] == (
                original_dimension,
                original_dimension,
            ):
                small_data[key] = value[np.ix_(selected, selected)]
            elif value.shape[0] == original_dimension:
                small_data[key] = value[selected]
            else:
                small_data[key] = value
        else:
            small_data[key] = value

    small_data["dimension"] = NUM_CUSTOMERS + 1
    small_data["edge_weight"] = raw_data["edge_weight"][
        np.ix_(selected, selected)
    ]
    small_data["demand"] = raw_data["demand"][selected]

    return small_data


data = load_small_cvrp_data()


class CvrpState:
    """
    CVRP 的一个解。

    routes:
        每辆车的客户访问顺序，不包含仓库 0。
        例如 [[1, 2, 3], [4, 5]] 表示两辆车。

    unassigned:
        暂时没有被安排进任何路线的客户。
        destroy 算子把客户放进这里，repair 算子再把客户插回路线。
    """

    def __init__(self, routes, unassigned=None):
        self.routes = routes
        self.unassigned = unassigned if unassigned is not None else []

    def copy(self):
        # routes 是列表套列表，必须深拷贝，避免破坏算子改到原解。
        return CvrpState(copy.deepcopy(self.routes), self.unassigned.copy())

    def objective(self):
        # ALNS 默认做最小化，这里目标函数是所有车辆路线的总距离。
        return sum(route_cost(route) for route in self.routes)

    @property
    def cost(self):
        return self.objective()

    def find_route(self, customer):
        # 找到某个客户当前在哪一条路线里。
        for route in self.routes:
            if customer in route:
                return route

        raise ValueError(f"Solution does not contain customer {customer}.")


def route_cost(route):
    """
    计算一条车路线的成本。

    route 不包含仓库 0，所以这里手动补成：
        0 -> customer ... -> 0
    """
    distances = data["edge_weight"]
    tour = [0] + [int(customer) for customer in route] + [0]

    return sum(
        distances[tour[idx]][tour[idx + 1]] for idx in range(len(tour) - 1)
    )


def neighbors(customer):
    """
    返回距离 customer 最近的其他客户，排除仓库 0。
    """
    locations = np.argsort(data["edge_weight"][int(customer)])
    return [int(location) for location in locations if int(location) != 0]


def nearest_neighbor():
    """
    构造初始解。

    思路：
    1. 从仓库 0 出发；
    2. 每次选择最近的未访问客户；
    3. 如果加入该客户会超过容量，就结束当前路线，开新车。
    """
    routes = []
    unvisited = set(range(1, data["dimension"]))

    while unvisited:
        route = [0]
        route_demands = 0

        while unvisited:
            current = route[-1]
            nearest = [nb for nb in neighbors(current) if nb in unvisited][0]

            if route_demands + data["demand"][nearest] > data["capacity"]:
                break

            route.append(nearest)
            unvisited.remove(nearest)
            route_demands += data["demand"][nearest]

        routes.append(route[1:])

    return CvrpState(routes)


CUSTOMERS_TO_REMOVE = max(1, int(0.1 * NUM_CUSTOMERS))

# 小规模算例不要一次删太多。这里最多破坏 1 条路线，每次删短片段。
AVG_ROUTE_FRACTION = 0.35
MAX_STRING_SIZE = max(1, int(NUM_CUSTOMERS * AVG_ROUTE_FRACTION))
MAX_STRING_REMOVALS = 1


def random_removal(state, rng):
    """
    破坏算子 1：随机删除一部分客户。

    被删除的客户：
    - 从 routes 中移除；
    - 加入 unassigned；
    - 等待 repair 算子重新插入。
    """
    destroyed = state.copy()

    customers = rng.choice(
        range(1, data["dimension"]), CUSTOMERS_TO_REMOVE, replace=False
    )

    for customer in customers:
        customer = int(customer)
        destroyed.unassigned.append(customer)
        route = destroyed.find_route(customer)
        route.remove(customer)

    return remove_empty_routes(destroyed)


def remove_empty_routes(state):
    """
    删除被破坏后变空的路线。
    """
    state.routes = [route for route in state.routes if len(route) != 0]
    return state


def string_removal(state, rng):
    """
    破坏算子 2：删除局部连续片段。

    它会随机选择一个中心客户，然后优先考虑这个中心附近的客户。
    小规模版本最多破坏 MAX_STRING_REMOVALS 条路线，避免一次删太多。
    """
    destroyed = state.copy()

    avg_route_size = max(
        1, int(np.mean([len(route) for route in state.routes]))
    )
    local_string_size = max(1, int(avg_route_size * AVG_ROUTE_FRACTION))
    max_string_size = min(MAX_STRING_SIZE, local_string_size)
    max_string_removals = min(len(state.routes), MAX_STRING_REMOVALS)

    destroyed_routes = []
    center = int(rng.integers(1, data["dimension"]))

    for customer in neighbors(center):
        if len(destroyed_routes) >= max_string_removals:
            break

        if customer in destroyed.unassigned:
            continue

        route = destroyed.find_route(customer)
        if route in destroyed_routes:
            continue

        customers = remove_string(route, customer, max_string_size, rng)
        destroyed.unassigned.extend(customers)
        destroyed_routes.append(route)

    return remove_empty_routes(destroyed)


def remove_string(route, customer, max_string_size, rng):
    """
    从一条路线中删除一段连续客户，且这段客户包含 customer。
    """
    size = int(rng.integers(1, min(len(route), max_string_size) + 1))
    start = route.index(customer) - int(rng.integers(size))
    indices = [idx % len(route) for idx in range(start, start + size)]

    removed_customers = []
    for idx in sorted(indices, reverse=True):
        removed_customers.append(int(route.pop(idx)))

    return removed_customers


def greedy_repair(state, rng):
    """
    修复算子：把 unassigned 中的客户重新插回路线。

    对每个待插入客户，寻找“可行且距离增加最少”的插入位置。
    如果没有任何可行位置，就为这个客户新开一条路线。
    """
    rng.shuffle(state.unassigned)

    while len(state.unassigned) != 0:
        customer = int(state.unassigned.pop())
        route, idx = best_insert(customer, state)

        if route is not None:
            route.insert(idx, customer)
        else:
            state.routes.append([customer])

    return state


def best_insert(customer, state):
    """
    为 customer 寻找最佳插入位置。

    最佳 = 插入后路线成本增加最少。
    如果所有路线都因为容量约束不可插入，则返回 (None, None)。
    """
    best_cost, best_route, best_idx = None, None, None

    for route in state.routes:
        for idx in range(len(route) + 1):
            if can_insert(customer, route):
                cost = insert_cost(customer, route, idx)

                if best_cost is None or cost < best_cost:
                    best_cost, best_route, best_idx = cost, route, idx

    return best_route, best_idx


def can_insert(customer, route):
    """
    检查容量约束：把 customer 加入 route 后是否超过车辆容量。
    """
    total = data["demand"][route].sum() + data["demand"][customer]
    return total <= data["capacity"]


def insert_cost(customer, route, idx):
    """
    计算把 customer 插入 route 的 idx 位置导致的距离增量。

    原来有一条边：
        pred -> succ

    插入后变成：
        pred -> customer -> succ

    增量就是：
        dist[pred][customer] + dist[customer][succ] - dist[pred][succ]
    """
    dist = data["edge_weight"]
    pred = 0 if idx == 0 else route[idx - 1]
    succ = 0 if idx == len(route) else route[idx]

    return dist[pred][customer] + dist[customer][succ] - dist[pred][succ]


def clean_route(route):
    """
    把 numpy 整数转为普通 int，避免输出 np.int64(...)。
    """
    return [int(customer) for customer in route]


def check_solution_feasible(state):
    """
    简单可行性检查：
    - 客户 1..NUM_CUSTOMERS 是否恰好出现一次；
    - 是否有重复客户；
    - 是否有遗漏客户；
    - 每条路线需求量是否不超过车辆容量。
    """
    expected = set(range(1, NUM_CUSTOMERS + 1))
    seen = []

    for route in state.routes:
        seen.extend(clean_route(route))

    seen_set = set(seen)
    duplicates = sorted(
        customer for customer in seen_set if seen.count(customer) > 1
    )
    missing = sorted(expected - seen_set)
    unexpected = sorted(seen_set - expected)

    capacity_violations = []
    for idx, route in enumerate(state.routes, start=1):
        demand = int(data["demand"][clean_route(route)].sum())
        if demand > data["capacity"]:
            capacity_violations.append((idx, demand))

    feasible = (
        len(seen) == NUM_CUSTOMERS
        and not duplicates
        and not missing
        and not unexpected
        and not capacity_violations
    )

    return {
        "feasible": feasible,
        "duplicates": duplicates,
        "missing": missing,
        "unexpected": unexpected,
        "capacity_violations": capacity_violations,
    }


def run_alns(destroy_operator, name, num_iterations=NUM_ITERATIONS):
    """
    运行一次 ALNS。

    destroy_operator 可以传入 random_removal 或 string_removal。
    repair_operator 这里固定使用 greedy_repair。
    """
    init = nearest_neighbor()

    alns = ALNS(rnd.default_rng(RANDOM_SEED))
    alns.add_destroy_operator(destroy_operator)
    alns.add_repair_operator(greedy_repair)

    select = RouletteWheel([25, 5, 1, 0], 0.8, 1, 1)
    accept = RecordToRecordTravel.autofit(
        init.objective(), 0.02, 0, num_iterations
    )
    stop = MaxIterations(num_iterations)

    start = time.perf_counter()
    result = alns.iterate(init, select, accept, stop)
    runtime = time.perf_counter() - start

    solution = result.best_state
    initial_objective = init.objective()
    best_objective = solution.objective()
    improvement = (
        (initial_objective - best_objective) / initial_objective * 100
    )
    feasibility = check_solution_feasible(solution)

    print("=" * 72)
    print(name)
    print(f"Initial objective: {initial_objective:,.2f}")
    print(f"Best objective:    {best_objective:,.2f}")
    print(f"Improvement:       {improvement:.2f}%")
    print(f"Number of routes:  {len(solution.routes)}")
    print(f"Runtime seconds:   {runtime:.3f}")
    print(f"feasible={feasibility['feasible']}")

    if not feasibility["feasible"]:
        print(f"  duplicates: {feasibility['duplicates']}")
        print(f"  missing: {feasibility['missing']}")
        print(f"  unexpected: {feasibility['unexpected']}")
        print(f"  capacity violations: {feasibility['capacity_violations']}")

    print("All routes:")
    for idx, route in enumerate(solution.routes, start=1):
        demand = int(data["demand"][clean_route(route)].sum())
        cost = route_cost(route)
        print(
            f"  Route {idx}: {clean_route(route)} "
            f"| demand={demand} | cost={cost:,.2f}"
        )

    return result


def main():
    print("CVRP ALNS small learning template")
    print(f"Customers: {NUM_CUSTOMERS}")
    print(f"Vehicle capacity: {data['capacity']}")
    print(f"Iterations: {NUM_ITERATIONS}")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Customers removed per random destroy: {CUSTOMERS_TO_REMOVE}")
    print(f"String avg route fraction: {AVG_ROUTE_FRACTION}")
    print(f"Max string size: {MAX_STRING_SIZE}")
    print(f"Max string removals: {MAX_STRING_REMOVALS}")

    run_alns(random_removal, "ALNS with random_removal")
    run_alns(string_removal, "ALNS with string_removal")


if __name__ == "__main__":
    main()
