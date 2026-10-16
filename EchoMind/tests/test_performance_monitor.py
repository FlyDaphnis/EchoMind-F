import asyncio

from agents.agent_orchestrator import AgentStats
from monitor.performance_monitor import PerformanceMonitor


class StatsSource:
    def __init__(self, stats):
        self.stats = stats

    def get_stats(self):
        return self.stats


def make_monitor(agent_total=1, agent_ms=15000, tool_total=0, tool_ms=0):
    agents = StatsSource({
        "technical_0": {
            "total": agent_total,
            "completed": agent_total,
            "success_rate": 1.0,
            "avg_ms": agent_ms,
            "routing_score": 1.0,
        }
    })
    tools = StatsSource({
        "knowledge_search": {
            "total": tool_total,
            "completed": tool_total,
            "success_rate": 1.0,
            "avg_latency_ms": tool_ms,
            "consecutive_fails": 0,
            "circuit_state": "closed",
        }
    })
    return PerformanceMonitor(agents, tools), agents, tools


def collect(monitor):
    asyncio.run(monitor._collect())


def test_agent_latency_alert_is_deduplicated_and_uses_14_second_threshold():
    monitor, agents, _ = make_monitor(agent_ms=13999)
    collect(monitor)
    assert monitor.summary()["active_alerts"] == []

    agents.stats["technical_0"].update(total=2, completed=2, avg_ms=14001)
    collect(monitor)
    first = monitor.summary()["active_alerts"]
    assert len(first) == 1
    assert first[0]["threshold"] == 14000

    collect(monitor)
    assert len(monitor.summary()["active_alerts"]) == 1
    assert len(monitor._alerts) == 1


def test_agent_alert_resolves_after_new_fast_call_and_reopens_on_regression():
    monitor, agents, _ = make_monitor()
    collect(monitor)
    assert len(monitor.summary()["active_alerts"]) == 1

    agents.stats["technical_0"].update(total=2, completed=2, avg_ms=13000)
    collect(monitor)
    assert monitor.summary()["active_alerts"] == []
    assert monitor._alerts[0].resolved is True

    agents.stats["technical_0"].update(total=3, completed=3, avg_ms=15000)
    collect(monitor)
    assert len(monitor.summary()["active_alerts"]) == 1
    assert len(monitor._alerts) == 2


def test_idle_sample_does_not_recheck_agent_or_tool_latency():
    monitor, agents, tools = make_monitor(tool_total=1, tool_ms=6000)
    collect(monitor)
    assert {alert["metric"] for alert in monitor.summary()["active_alerts"]} == {
        "agent_avg_ms:technical_0", "tool_avg_ms:knowledge_search"
    }

    agents.stats["technical_0"]["avg_ms"] = 12000
    tools.stats["knowledge_search"]["avg_latency_ms"] = 1000
    collect(monitor)
    assert {alert["metric"] for alert in monitor.summary()["active_alerts"]} == {
        "agent_avg_ms:technical_0", "tool_avg_ms:knowledge_search"
    }

    agents.stats["technical_0"]["total"] = 2
    agents.stats["technical_0"]["completed"] = 2
    tools.stats["knowledge_search"]["total"] = 2
    tools.stats["knowledge_search"]["completed"] = 2
    collect(monitor)
    assert monitor.summary()["active_alerts"] == []


def test_success_rate_alert_is_deduplicated_and_resolved():
    monitor, agents, _ = make_monitor(agent_ms=0)
    agents.stats["technical_0"]["success_rate"] = 0.5
    collect(monitor)
    collect(monitor)
    assert len(monitor.summary()["active_alerts"]) == 1
    assert len(monitor._alerts) == 1

    agents.stats["technical_0"].update(total=2, completed=2, success_rate=1.0)
    collect(monitor)
    assert monitor.summary()["active_alerts"] == []


def test_latency_is_checked_after_call_finishes_not_when_it_starts():
    monitor, agents, _ = make_monitor(agent_total=1, agent_ms=0)
    agents.stats["technical_0"]["completed"] = 0
    collect(monitor)
    assert monitor.summary()["active_alerts"] == []

    agents.stats["technical_0"].update(completed=1, avg_ms=15000)
    collect(monitor)
    assert [alert["metric"] for alert in monitor.summary()["active_alerts"]] == [
        "agent_avg_ms:technical_0"
    ]


def test_latency_routing_penalty_uses_same_14_second_threshold():
    assert PerformanceMonitor._routing_penalty(1.0, 14000) == 0
    assert PerformanceMonitor._routing_penalty(1.0, 15000) > 0


def test_summary_returns_all_distinct_active_alerts():
    monitor, agents, _ = make_monitor()
    agents.stats = {
        f"technical_{i}": {**agents.stats["technical_0"]}
        for i in range(12)
    }
    collect(monitor)
    assert len(monitor.summary()["active_alerts"]) == 12


def test_agent_success_rate_counts_only_completed_calls():
    stats = AgentStats(total=1)
    assert stats.success_rate == 1.0  # 首次调用仍在处理中

    stats.total = 2
    stats.completed = 1
    stats.success = 1
    assert stats.success_rate == 1.0  # 另一调用在处理中，不降低已完成调用的成功率

    stats.completed = 2
    assert stats.success_rate == 0.5  # 第二次调用失败后才计入分母
