from croc.rl.gates import PromotionGates


def test_gate_rejects_regressions():
    gates = PromotionGates()
    baseline = {"sharpe": 1.0, "max_drawdown": 0.2, "win_rate": 0.55, "latency_p99": 20.0}
    candidate = {"sharpe": 0.8, "max_drawdown": 0.3, "win_rate": 0.50, "latency_p99": 25.0}
    result = gates.evaluate(candidate, baseline, {"candidate": candidate, "baseline": baseline})
    assert not result.passed
    assert "Sharpe ratio regressed" in result.reasons
    assert "Max drawdown exceeded baseline" in result.reasons
    assert "Win rate regressed" in result.reasons
    assert "Latency regression" in result.reasons
