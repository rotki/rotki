"""Macro benchmark harness for the measurement framework.

See docs/designs/perf_and_integration_framework.md (§4) for the design.

Boots the real backend on golden profiles built by tools.scenarios and times
a registry of user-visible operations. ``run`` produces a structured result
for one checkout; ``compare`` runs base and head interleaved on the same
machine (git worktree) and reports per-operation deltas.

Usage:
    uv run python -m tools.bench run --profile small whale
    uv run python -m tools.bench compare --base develop
"""
