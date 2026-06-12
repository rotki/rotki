"""Local mock for the backend's external HTTP services (design §3.3).

Runs inside the bench runner process, or standalone for harnesses outside
python (``python -m tools.bench.mockserver --state <chain_state.json>``
prints ``MOCK_URL=...`` and serves until terminated — the contract suite
runner uses this). The backend under test is launched through
launch_backend.py, which redirects every non-localhost HTTP request here
(with the original host preserved in a header), so no traffic ever leaves
the machine and every external dependency answers instantly and
deterministically.

Chain answers (native + ERC-20 balances) come from the profile's
chain_state.json when one is given: the scenario generator writes it
alongside the same balances in expected.json, so what the mock serves and
what correctness suites expect share one source of truth.

Endpoints:
- ``/rpc/<chain_id>``: minimal JSON-RPC node. The bench harness registers it
  as the only active rpc node via the backend API. eth_call understands the
  rotki balance-scanner contract and returns deterministic per-address
  balances; everything else gets benign static answers.
- redirected requests (identified by the X-Bench-Original-Host header) are
  answered per service: etherscan-style indexers get empty-but-valid
  responses, beaconchain gets an empty validator set, everything unknown
  gets a fast 404 and is counted in ``unhandled`` so silent gaps are
  impossible.
"""
import json
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING, Any, Final
from urllib.parse import parse_qs, urlsplit

from eth_abi import decode as abi_decode, encode as abi_encode
from eth_utils import function_signature_to_4byte_selector

if TYPE_CHECKING:
    from pathlib import Path

ORIGINAL_HOST_HEADER: Final = 'X-Bench-Original-Host'

# rotki balance scanner contract (ROTKI_BALANCE_SCANNER in the global DB)
SCANNER_ETHER_BALANCES: Final = function_signature_to_4byte_selector('ether_balances(address[])')
SCANNER_TOKENS_BALANCE: Final = function_signature_to_4byte_selector('tokens_balance(address,address[])')  # noqa: E501
SCANNER_TOKEN_BALANCES: Final = function_signature_to_4byte_selector('token_balances(address[],address)')  # noqa: E501
# multicall, used by many module queries
MULTICALL_AGGREGATE: Final = function_signature_to_4byte_selector('aggregate((address,bytes)[])')
MULTICALL_TRY_AGGREGATE: Final = function_signature_to_4byte_selector('tryAggregate(bool,(address,bytes)[])')  # noqa: E501
MULTICALL_TRY_BLOCK_AGGREGATE: Final = function_signature_to_4byte_selector('tryBlockAndAggregate(bool,(address,bytes)[])')  # noqa: E501

MOCK_BLOCK_NUMBER: Final = 0x14FD2E0  # fixed "latest" block
MOCK_BLOCK_TIMESTAMP: Final = 1767225600  # the frozen scenario clock


def deterministic_wei_balance(address: str) -> int:
    """A stable native balance (0-10 units, 18 decimals) derived from the address"""
    return (int(address, 16) % 10_000) * 10**15


class ChainState:
    """On-chain holdings served by the mock, loaded from a profile's
    chain_state.json (written by the scenario generator, which also emits
    the same balances into expected.json — one source of truth for both).

    Addresses outside the state fall back to the address-derived
    deterministic balance so the mock still answers for anything a module
    probes; unknown tokens are zero."""

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self._chains: dict[str, dict[str, Any]] = {
            chain_id: {address.lower(): holdings for address, holdings in accounts.items()}
            for chain_id, accounts in (state or {}).items()
        }

    @classmethod
    def from_profile(cls, data_dir: 'Path') -> 'ChainState':
        state_file = data_dir / 'chain_state.json'
        if not state_file.is_file():
            return cls()
        return cls(json.loads(state_file.read_text(encoding='utf8')))

    def native(self, chain_id: int, address: str) -> int:
        holdings = self._chains.get(str(chain_id), {}).get(address.lower())
        if holdings is None:
            return deterministic_wei_balance(address)
        return int(holdings['native'])

    def token(self, chain_id: int, token_address: str, holder: str) -> int:
        holdings = self._chains.get(str(chain_id), {}).get(holder.lower())
        if holdings is None:
            return 0
        return int(holdings['tokens'].get(token_address.lower(), 0))


def _call_result(data: bytes, state: ChainState, chain_id: int) -> tuple[bool, bytes]:
    """Answer one contract call's data, recursing through multicall.
    Returns (known, payload): unknown selectors report as reverted inside
    tryAggregate so module code skips them through its own failure handling
    instead of wrongly decoding a fabricated value."""
    selector, arguments = data[:4], data[4:]
    if selector == SCANNER_ETHER_BALANCES:
        (addresses,) = abi_decode(['address[]'], arguments)
        return True, abi_encode(
            ['uint256[]'],
            [[state.native(chain_id, address) for address in addresses]],
        )
    if selector == SCANNER_TOKENS_BALANCE:
        holder, tokens = abi_decode(['address', 'address[]'], arguments)
        return True, abi_encode(
            ['uint256[]'],
            [[state.token(chain_id, token, holder) for token in tokens]],
        )
    if selector == SCANNER_TOKEN_BALANCES:
        addresses, token = abi_decode(['address[]', 'address'], arguments)
        return True, abi_encode(
            ['uint256[]'],
            [[state.token(chain_id, token, address) for address in addresses]],
        )
    if selector == MULTICALL_AGGREGATE:
        (calls,) = abi_decode(['(address,bytes)[]'], arguments)
        return True, abi_encode(
            ['uint256', 'bytes[]'],
            [
                MOCK_BLOCK_NUMBER,
                # aggregate() inner calls must succeed; unknowns get a zero word
                [
                    _call_result(call_data, state, chain_id)[1] or bytes(32)
                    for _, call_data in calls
                ],
            ],
        )
    if selector in (MULTICALL_TRY_AGGREGATE, MULTICALL_TRY_BLOCK_AGGREGATE):
        _, calls = abi_decode(['bool', '(address,bytes)[]'], arguments)
        results = [_call_result(call_data, state, chain_id) for _, call_data in calls]
        if selector == MULTICALL_TRY_AGGREGATE:
            return True, abi_encode(['(bool,bytes)[]'], [results])
        return True, abi_encode(
            ['uint256', 'bytes32', '(bool,bytes)[]'],
            [MOCK_BLOCK_NUMBER, b'\xab' * 32, results],
        )
    return False, b''  # unknown selector


def _rpc_result(payload: dict[str, Any], chain_id: int, state: ChainState) -> Any:
    """Answer one JSON-RPC request body"""
    method = payload.get('method', '')
    params = payload.get('params', [])
    if method == 'eth_chainId':
        return hex(chain_id)
    if method == 'net_version':
        return str(chain_id)
    if method == 'web3_clientVersion':
        return 'rotki-bench-mock/1.0'
    if method == 'eth_blockNumber':
        return hex(MOCK_BLOCK_NUMBER)
    if method == 'eth_syncing':
        return False
    if method == 'eth_gasPrice':
        return '0x3b9aca00'
    if method == 'eth_getCode':
        return '0x60806040'  # non-empty: contracts exist
    if method == 'eth_getBalance':
        return hex(state.native(chain_id, params[0]))
    if method == 'eth_getBlockByNumber':
        return {
            'number': hex(MOCK_BLOCK_NUMBER),
            'hash': '0x' + 'ab' * 32,
            'parentHash': '0x' + 'cd' * 32,
            'timestamp': hex(MOCK_BLOCK_TIMESTAMP),
            'gasLimit': '0x1c9c380',
            'gasUsed': '0xf4240',
            'baseFeePerGas': '0x3b9aca00',
            'miner': '0x' + '00' * 20,
            'difficulty': '0x0',
            'totalDifficulty': '0x0',
            'extraData': '0x',
            'size': '0x1000',
            'logsBloom': '0x' + '00' * 256,
            'transactions': [],
            'uncles': [],
        }
    if method == 'eth_call':
        data = params[0].get('data', '0x') if params else '0x'
        raw = bytes.fromhex(data[2:]) if data.startswith('0x') else b''
        known, payload = _call_result(raw, state, chain_id)
        return '0x' + (payload if known else bytes(32)).hex()
    if method == 'eth_getTransactionByHash':
        # answered so the node-inquirer's pruned-node probe finds its tx
        return {
            'hash': params[0],
            'nonce': '0x1',
            'blockHash': '0x' + 'ab' * 32,
            'blockNumber': hex(MOCK_BLOCK_NUMBER - 1000),
            'transactionIndex': '0x0',
            'from': '0x' + '11' * 20,
            'to': '0x' + '22' * 20,
            'value': '0xde0b6b3a7640000',
            'gas': '0x5208',
            'gasPrice': '0x3b9aca00',
            'input': '0x',
            'type': '0x2',
            'v': '0x1',
            'r': '0x' + '01' * 32,
            's': '0x' + '02' * 32,
        }
    raise KeyError(method)


def _etherscan_response(query: dict[str, list[str]], state: ChainState) -> dict[str, Any]:
    """Empty-but-valid etherscan-style answers"""
    action = query.get('action', [''])[0]
    chain_id = int(query.get('chainid', ['1'])[0])  # etherscan v2 carries the chain in the query
    if action == 'balance':
        address = query.get('address', ['0x0'])[0]
        return {'status': '1', 'message': 'OK', 'result': str(state.native(chain_id, address))}
    if action == 'balancemulti':
        addresses = query.get('address', [''])[0].split(',')
        return {'status': '1', 'message': 'OK', 'result': [
            {'account': address, 'balance': str(state.native(chain_id, address))}
            for address in addresses if address
        ]}
    if action == 'eth_blockNumber':  # proxy module
        return {'jsonrpc': '2.0', 'id': 1, 'result': hex(MOCK_BLOCK_NUMBER)}
    if action == 'eth_call':  # proxy module: same contract-call logic as the rpc node
        data = query.get('data', ['0x'])[0]
        raw = bytes.fromhex(data[2:]) if data.startswith('0x') else b''
        known, payload = _call_result(raw, state, chain_id)
        return {'jsonrpc': '2.0', 'id': 1, 'result': '0x' + (payload if known else bytes(32)).hex()}  # noqa: E501
    if action == 'getblocknobytime':
        return {'status': '1', 'message': 'OK', 'result': str(MOCK_BLOCK_NUMBER)}
    # txlist, txlistinternal, tokentx, getLogs, ...: nothing found
    return {'status': '0', 'message': 'No transactions found', 'result': []}


class MockExternalServices:
    """Threaded local server answering all redirected external traffic"""

    def __init__(self, chain_state: ChainState | None = None) -> None:
        self.state = chain_state if chain_state is not None else ChainState()
        self.unhandled: Counter[str] = Counter()
        self.served = 0
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        assert self._httpd is not None, 'mock server not started'
        return f'http://127.0.0.1:{self._httpd.server_address[1]}'

    def start(self) -> None:
        mock = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                """Silence per-request stderr logging"""

            def _respond(self, status: int, body: Any) -> None:
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                mock.served += 1

            def _handle(self) -> None:
                split = urlsplit(self.path)
                length = int(self.headers.get('Content-Length') or 0)
                body = self.rfile.read(length) if length else b''
                original_host = self.headers.get(ORIGINAL_HOST_HEADER, '')

                if split.path == '/__mock__/stats':  # introspection for the harnesses
                    self._respond(200, {
                        'served': mock.served,
                        'unhandled': dict(mock.unhandled),
                    })
                    return

                if split.path.startswith('/rpc/'):  # our registered rpc node
                    chain_id = int(split.path.split('/')[2])
                    payload = json.loads(body)
                    requests_list = payload if isinstance(payload, list) else [payload]
                    answers = []
                    for entry in requests_list:
                        try:
                            result = _rpc_result(entry, chain_id, mock.state)
                        except (KeyError, IndexError, ValueError):
                            mock.unhandled[f'rpc:{entry.get("method")}'] += 1
                            answers.append({
                                'jsonrpc': '2.0',
                                'id': entry.get('id'),
                                'error': {'code': -32601, 'message': 'bench-mock: unhandled'},
                            })
                            continue
                        answers.append(
                            {'jsonrpc': '2.0', 'id': entry.get('id'), 'result': result},
                        )
                    self._respond(200, answers if isinstance(payload, list) else answers[0])
                    return

                if 'etherscan' in original_host or 'blockscout' in original_host or 'routescan' in original_host:  # noqa: E501
                    self._respond(200, _etherscan_response(parse_qs(split.query), mock.state))
                    return

                if 'beacon' in original_host:
                    if 'node/version' in split.path:  # beacon node API client
                        self._respond(200, {'data': {'version': 'rotki-bench-mock/1.0'}})
                    elif 'beaconcha.in' in original_host:  # beaconcha.in explorer API
                        self._respond(200, {'status': 'OK', 'data': []})
                    else:  # other beacon node API paths (validators, spec, ...)
                        self._respond(200, {'data': []})
                    return

                # anything else: fast, visible refusal
                mock.unhandled[f'{original_host}{split.path}'] += 1
                self._respond(404, {'message': 'rotki-bench-mock: service not mocked'})

            do_GET = _handle  # noqa: N815  # names dictated by BaseHTTPRequestHandler
            do_POST = _handle  # noqa: N815  # names dictated by BaseHTTPRequestHandler
            do_PUT = _handle  # noqa: N815  # names dictated by BaseHTTPRequestHandler
            do_HEAD = _handle  # noqa: N815  # names dictated by BaseHTTPRequestHandler

        self._httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


def main() -> None:
    """Standalone entrypoint: serve until terminated, announcing the url on
    stdout so a spawning harness can pick it up."""
    import argparse
    import time
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--state',
        type=Path,
        default=None,
        help='path to a profile chain_state.json to serve chain answers from',
    )
    args = parser.parse_args()
    chain_state = ChainState() if args.state is None else ChainState(
        json.loads(args.state.read_text(encoding='utf8')),
    )
    mock = MockExternalServices(chain_state=chain_state)
    mock.start()
    print(f'MOCK_URL={mock.url}', flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        mock.stop()


if __name__ == '__main__':
    main()
