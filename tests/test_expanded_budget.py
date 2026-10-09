from concurrent.futures import ThreadPoolExecutor

import pytest

from research_v2.expanded_generation import Budget, BudgetExceeded, reported_cost


POLICY = {"cap_usd": 1.0, "prior_diagnostic_reservations_usd": .1, "codex_prior_output_reservations": 10,
          "codex_output_limit_exclusive": 1000, "input_cache_write_safety_multiplier": 1.25}


def test_reserve_settle_unknown_and_cap(tmp_path):
    budget = Budget(tmp_path / "budget.sqlite3", POLICY)
    first, attempt = budget.reserve("test", "a", .5, 100)
    assert attempt == 1
    with pytest.raises(BudgetExceeded):
        budget.reserve("test", "b", .5, 100)
    budget.settle(first, .05, 50)
    budget.reserve("test", "b", .5, 100)
    assert budget.status()["reference_cost_used_or_reserved_usd"] == .65
    with pytest.raises(ValueError, match="already settled"):
        budget.settle(first, 0, 0)
    with pytest.raises(ValueError, match="policy changed"):
        Budget(budget.path, {**POLICY, "cap_usd": 100})


def test_parallel_reservations_cannot_overspend(tmp_path):
    budget = Budget(tmp_path / "budget.sqlite3", POLICY)
    def reserve(i):
        try:
            budget.reserve("model", str(i), .2, 10)
            return True
        except BudgetExceeded:
            return False
    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(reserve, range(20))) == 4
    assert budget.status()["reference_cost_used_or_reserved_usd"] == .9


def test_token_and_attempt_limits_survive_restart(tmp_path):
    budget = Budget(tmp_path / "budget.sqlite3", POLICY)
    budget.reserve("codex51", "a", .01, 500)
    with pytest.raises(BudgetExceeded, match="token_cap"):
        Budget(budget.path, POLICY).reserve("codex51", "b", .01, 490)
    for _ in range(3):
        budget.reserve("test", "repeat", .01, 10)
    with pytest.raises(BudgetExceeded, match="attempt_limit"):
        budget.reserve("test", "repeat", .01, 10)


def test_reasoning_tokens_are_included_and_missing_usage_not_zero():
    config = {"api": "gemini_native", "input_usd_per_million": 1, "output_usd_per_million": 10}
    assert reported_cost({}, config, POLICY) is None
    cost, output = reported_cost({"usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 200, "thoughtsTokenCount": 300}}, config, POLICY)
    assert output == 500 and cost == .005125
    config["api"] = "azure_responses"
    assert reported_cost({"usage": {"input_tokens": -1, "output_tokens": 5}}, config, POLICY) is None
