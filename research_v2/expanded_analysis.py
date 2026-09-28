"""Explicit v3 analysis entry point; no process-global study-path monkeypatching."""
from __future__ import annotations

import argparse
import json

from .expanded_study import BASE, effective_plan
from .transfer_extension import run
from .transfer_verify import replay_and_verify, verify

EXTENSION = BASE / "extensions/jql_v1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "verify", "replay"))
    parser.add_argument("--models", nargs="+", required=True)
    args = parser.parse_args()
    if not set(args.models) <= set(effective_plan()["active_models"]):
        parser.error("Choose active expanded-study models")
    for model in args.models:
        if args.action == "run":
            result = run(model, study=BASE, extension_base=EXTENSION)
        elif args.action == "verify":
            result = verify(model, BASE, EXTENSION)
        else:
            result = replay_and_verify(model, BASE, EXTENSION)
        print(json.dumps({k: v for k, v in result.items() if k not in {"inputs", "output_hashes"}}, indent=2))


if __name__ == "__main__":
    main()
