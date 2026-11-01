"""规则引擎单元测试（不依赖数据库 / LLM，可离线运行）。

运行：pytest -q
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from rule_engine import RuleEngine

BASE = datetime(2026, 1, 1, 8, 0, 0)


def _feed(engine: RuleEngine, sensor: str, offsets: list[float]) -> None:
    for seconds in offsets:
        engine.record_action(sensor, BASE + timedelta(seconds=seconds))


def test_no_history_produces_no_alert():
    engine = RuleEngine()
    assert engine.evaluate() == []
    assert engine.check_gripper_cycle() is None
    assert engine.check_vacuum_delay() is None


def test_gripper_cycle_below_threshold_is_normal():
    engine = RuleEngine()
    _feed(engine, "夹爪", [0, 1, 2, 3, 4, 5])  # 平均节拍 1s
    assert engine.check_gripper_cycle() is None


def test_gripper_slow_cycle_is_flagged():
    engine = RuleEngine()
    _feed(engine, "夹爪", [0, 4, 8, 12, 16, 20])  # 平均节拍 4s > 3.5s
    result = engine.check_gripper_cycle()
    assert result is not None
    assert result["rule"] == "gripper_cycle"
    assert result["conclusion"] == "疑似异常"
    assert result["confidence"] == "中"  # 4s 未到 5s
    assert result["avg_cycle"] == pytest.approx(4.0)


def test_gripper_very_slow_cycle_raises_confidence():
    engine = RuleEngine()
    _feed(engine, "夹爪", [0, 6, 12, 18, 24, 30])  # 平均节拍 6s
    result = engine.check_gripper_cycle()
    assert result is not None
    assert result["confidence"] == "高"


def test_gripper_needs_min_samples():
    engine = RuleEngine()
    _feed(engine, "夹爪", [0, 10, 20])  # 样本不足
    assert engine.check_gripper_cycle() is None


def test_vacuum_to_gripper_delay_is_flagged():
    engine = RuleEngine()
    engine.record_action("真空发生器", BASE)
    engine.record_action("夹爪", BASE + timedelta(seconds=2))  # 延迟 2s > 1.5s
    result = engine.check_vacuum_delay()
    assert result is not None
    assert result["rule"] == "vacuum_delay"
    assert result["avg_delay"] == pytest.approx(2.0)


def test_vacuum_to_gripper_fast_delay_is_normal():
    engine = RuleEngine()
    engine.record_action("真空发生器", BASE)
    engine.record_action("夹爪", BASE + timedelta(seconds=0.5))
    assert engine.check_vacuum_delay() is None


def test_delay_beyond_window_is_ignored():
    engine = RuleEngine()
    engine.record_action("真空发生器", BASE)
    engine.record_action("夹爪", BASE + timedelta(seconds=8))  # 超出 5s 关联窗口
    assert engine.check_vacuum_delay() is None


def test_evaluate_aggregates_multiple_hits():
    engine = RuleEngine()
    _feed(engine, "夹爪", [0, 4, 8, 12, 16, 20])
    engine.record_action("真空发生器", BASE + timedelta(seconds=1))
    results = engine.evaluate()
    assert {r["rule"] for r in results} == {"gripper_cycle", "vacuum_delay"}


def test_history_is_capped_at_fifty():
    engine = RuleEngine()
    _feed(engine, "夹爪", [i * 0.1 for i in range(120)])
    assert len(engine.action_history["夹爪"]) == 50
