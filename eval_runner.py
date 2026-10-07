"""Single-command deterministic eval entry (design section 6).

Inserts its own directory on sys.path so it runs from any working directory
(absolute-path friendly). Runs the four-check contract floor + the version guard
(contract_checks) and the five deterministic scoring checks (scoring) — ten
checks total, NO model and NO network. With --model it additionally runs the
optional live model-in-the-loop scoring (needs Strands + Bedrock).

Run:
    cd "<project dir>"; python eval_runner.py
    python "<project dir>/eval_runner.py"     # absolute-path form
    python eval_runner.py --model             # + optional live scoring
"""
import sys
import pathlib
import argparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from evaluation import contract_checks, scoring


def main() -> None:
    parser = argparse.ArgumentParser(description="Conference Concierge eval runner")
    parser.add_argument(
        "--model",
        action="store_true",
        help="also run optional model-in-the-loop scoring (needs Bedrock)",
    )
    args = parser.parse_args()

    contract_checks.run_all()      # the 4-check floor + version guard (#1-#4, #10)
    scoring.run_all()              # deterministic scored quality checks (#5-#9)

    if args.model:
        from evaluation import model_in_the_loop
        model_in_the_loop.run_all()

    print("\nAll eval checks passed.")


if __name__ == "__main__":
    main()
