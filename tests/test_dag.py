import pytest

from router.core.dag import CycleError, Node, levels, topological_order, validate


def test_topological_order_respects_deps():
    nodes = [Node("c", ("a", "b")), Node("a"), Node("b", ("a",))]
    order = topological_order(nodes)
    assert order.index("a") < order.index("b") < order.index("c")


def test_levels_group_parallelizable_tasks():
    nodes = [Node("a"), Node("b"), Node("c", ("a", "b")), Node("d", ("c",))]
    lv = levels(nodes)
    assert lv[0] == ["a", "b"]   # no deps -> first batch, runnable in parallel
    assert lv[1] == ["c"]
    assert lv[2] == ["d"]


def test_cycle_detected():
    nodes = [Node("a", ("b",)), Node("b", ("a",))]
    with pytest.raises(CycleError):
        topological_order(nodes)


def test_unknown_dependency_rejected():
    with pytest.raises(ValueError):
        validate([Node("a", ("ghost",))])


def test_duplicate_id_rejected():
    with pytest.raises(ValueError):
        topological_order([Node("a"), Node("a")])
