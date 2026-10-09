"""Versioned entry point for the unchanged shift-versus-contraction analysis."""
import argparse
import json

from .expanded_study import BASE
from .shift_contraction import replay_and_verify, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "replay"))
    parser.add_argument("--models", nargs="+", required=True)
    args = parser.parse_args()
    results = [(run if args.action == "run" else replay_and_verify)(model, BASE, BASE / "extensions/jql_v1") for model in args.models]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
