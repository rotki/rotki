"""Backend launcher for benchmark runs: no shipped code is modified.

Mirrors ``python -m rotkehlchen`` (gevent monkey-patching first) but applies
one surgical patch before starting: every HTTP request leaving this process
for a non-localhost destination is transparently redirected to the local mock
server (ROTKI_BENCH_MOCK_URL), with the original host preserved in a header
so the mock can answer per service. This guarantees zero network egress
during benchmarks and turns any unmocked dependency into a fast, visible
refusal instead of silent nondeterministic network traffic.

The same pattern as the premium monkeypatch idea (design §5.3): the patch
lives in the harness, never in shipped backend code.
"""
from gevent import monkey  # isort:skip
monkey.patch_all()  # isort:skip

import os
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests.adapters

MOCK_URL = os.environ['ROTKI_BENCH_MOCK_URL']
ORIGINAL_HOST_HEADER = 'X-Bench-Original-Host'

_mock_parts = urlsplit(MOCK_URL)
_local_hosts = {'127.0.0.1', 'localhost', '::1'}
_original_send = requests.adapters.HTTPAdapter.send


def _redirecting_send(self: Any, request: Any, **kwargs: Any) -> Any:
    parts = urlsplit(request.url)
    if (parts.hostname or '') not in _local_hosts:
        request.headers[ORIGINAL_HOST_HEADER] = parts.hostname or ''
        request.url = urlunsplit(
            (_mock_parts.scheme, _mock_parts.netloc, parts.path, parts.query, ''),
        )
        kwargs['verify'] = False  # the mock is plain http; nothing real is contacted
    return _original_send(self, request, **kwargs)


requests.adapters.HTTPAdapter.send = _redirecting_send

from rotkehlchen.__main__ import main

main()
