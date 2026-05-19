# Mock RPC Server

A record/replay mock server that intercepts JSON-RPC calls from the backend during E2E tests, eliminating flaky failures caused by rate limiting from public blockchain nodes.

## How it works

The mock server sits between the backend and real blockchain RPC nodes. After login, the test setup replaces the backend's default RPC nodes with the mock server and switches to a test-specific cassette file.

```
Playwright → Frontend → Backend API → Mock RPC Server → (record: real node / replay: cassette)
```

## Modes

### Replay (default)

Serves recorded responses from cassette files. No real RPC calls are made.

```bash
# Run balance tests using recorded cassettes
GROUP=balances pnpm run test:e2e
```

### Record

Forwards requests to a real RPC node and saves the responses to cassette files.

```bash
# Record using a public RPC endpoint
MOCK_RPC_MODE=record MOCK_RPC_TARGET=https://eth.llamarpc.com GROUP=balances pnpm run test:e2e
```

Alternative RPC targets (if one is rate-limited):
- `https://rpc.ankr.com/eth`
- `https://cloudflare-eth.com`
- `https://ethereum-rpc.publicnode.com`

For faster/more reliable recording, use a private RPC endpoint (Alchemy, Infura, etc.).

### Recording non-EVM chains

Solana, Polkadot (DOT) and Kusama (KSM) speak JSON-RPC and are mocked the same way. Use a target appropriate for the chain when recording:

```bash
# Solana
MOCK_RPC_MODE=record MOCK_RPC_TARGET=https://api.mainnet-beta.solana.com \
  pnpm exec playwright test specs/balances/solana-accounts.spec.ts

# Polkadot — point at the public HTTP RPC (not the ws:// one)
MOCK_RPC_MODE=record MOCK_RPC_TARGET=https://rpc.polkadot.io \
  pnpm exec playwright test specs/balances/substrate-accounts.spec.ts
```

Substrate chains (DOT/KSM) don't use the multi-node API like EVM/Solana — the mock helper sets their single `dot_rpc_endpoint`/`ksm_rpc_endpoint` user setting instead. The setup is otherwise identical: list the chain in `rpcMockChains` (e.g. `['DOT']`).

## Cassette files

Cassettes are stored in `tests/e2e/cassettes/rpc/{name}.json`. Each test suite specifies its cassette name:

```typescript
ctx = await createLoggedInContext(browser, request, {
  disableModules: true,
  rpcMockCassette: 'blockchain-balances', // → cassettes/rpc/blockchain-balances.json
});
```

After recording, commit the cassette files to the repository so CI runs in replay mode.

## When to re-record

Re-record cassettes when:
- Test addresses change
- The global token database is updated (changes balance scanner call data)
- New blockchain interactions are added to a test

## Server endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check (used by Playwright to detect readiness) |
| `/cassette` | POST | Switch cassette: `{ "name": "blockchain-balances" }` |
| `/save` | POST | Force-save current cassette to disk |
| `/stats` | GET | Current server state (mode, cassette, entry count) |
| `/` | POST | JSON-RPC handler (single or batch requests) |

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MOCK_RPC_MODE` | `replay` | `record` or `replay` |
| `MOCK_RPC_TARGET` | _(none)_ | Target RPC URL (required in record mode) |
| `MOCK_RPC_PORT` | `30304` | Port the mock server listens on |
