"""Evaluation suite: deterministic contract floor + scoring + version guard, and
an optional model-in-the-loop mode.

The deterministic path (contract_checks + scoring, ten checks total) runs with
NO model and NO network, importing only stdlib + project modules. The optional
model_in_the_loop module is imported only behind eval_runner.py --model and is
never required for the core eval to pass.
"""
