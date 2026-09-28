"""Credential selection is explicit transport configuration, not a model change."""
from copy import deepcopy

import pytest

from research_v2.parallel_generation import credential_config
from research_v2.providers import connection


def test_explicit_credential_preserves_frozen_config():
    frozen = {"api": "gemini_native", "model": "test-model", "key_env": "gemchat",
              "run_reservation_cap_usd": 10, "thinking_level": "minimal"}
    before = deepcopy(frozen)
    selected = credential_config(frozen, "gemtest")
    assert frozen == before
    assert selected == {**frozen, "key_env": "gemtest"}
    endpoint, headers = connection(selected, {"gemchat": "dummy-old", "gemtest": "dummy-new"})
    assert endpoint == connection(frozen, {"gemchat": "dummy-old"})[0]
    assert headers == {"x-goog-api-key": "dummy-new"}
    assert credential_config(frozen) == frozen


@pytest.mark.parametrize("name", ["", "not a name", "token=secret", "../api.env", "0bad"])
def test_rejects_non_variable_names(name):
    with pytest.raises(ValueError, match="environment variable name"):
        credential_config({"key_env": "gemchat"}, name)


def test_missing_selected_key_fails_without_fallback():
    config = credential_config({"key_env": "gemchat", "api": "gemini_native", "model": "test-model"}, "gemtest")
    with pytest.raises(ValueError, match="Missing credential variable gemtest"):
        connection(config, {"gemchat": "dummy-existing"})
