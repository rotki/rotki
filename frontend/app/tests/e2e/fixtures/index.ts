/**
 * Test environment configuration for E2E tests.
 */
export const testEnv = {
  PASSWORD: '1234',
  ETH_ADDRESS: '0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea',
  BTC_ADDRESS: '3PFo18vaPMSXFTt6zUDGk3UoPjD56QLXjh',
  // Solana fixture wallet for the account-add e2e. Picked for a non-zero SOL
  // balance (so the "USD value > 0" assertion has something real to verify) and
  // zero SPL tokens, which keeps the recorded RPC surface minimal: no per-mint
  // getAccountInfo metadata calls, so the cassette stays a handful of entries
  // instead of thousands. Independent of the backend unit-test address in
  // rotkehlchen/tests/unit/test_solana.py, which deliberately needs tokens/stake.
  // WARNING: avoid exercising transaction-history fetching against this address;
  // it would query signatures and inflate the cassette.
  SOLANA_ADDRESS: '8GbwASqdpw4dVcwbWUxbHXMrjyQx2aKkoBR5H1GJF8iD',
  // Stable Polkadot fixture wallet — picked because it holds a non-trivial,
  // long-running DOT balance, so the test's "USD value > 0" assertion is
  // stable across re-recordings.
  POLKADOT_ADDRESS: '13UVJyLnbVp9RBZYFwFGyDvVd1y27Tt8tkntv6Q7JVPhFsTB',
  KRAKEN_API_KEY: 'a39939bffed348299c6a859ca3f9a41e',
  KRAKEN_API_SECRET: '68203af4221446a08d156bb3a4fd27dc',
};
