"""Golden user profile generation for the measurement framework.

See docs/designs/perf_and_integration_framework.md (§3) for the design.

This package builds deterministic, realistic user data directories that the
real rotki backend can boot, used as the substrate for both integration
correctness checks and performance benchmarks. Profiles are generated at the
current DB schema version (never committed as binaries) and cached
content-addressed under ~/.cache/rotki-scenarios.

Usage:
    uv run python -m tools.scenarios build --profile whale --output /tmp/whale-data
"""
