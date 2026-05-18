/**
 * Test environment configuration for E2E tests.
 */
export const testEnv = {
  PASSWORD: '1234',
  ETH_ADDRESS: '0x443E1f9b1c866E54e914822B7d3d7165EdB6e9Ea',
  BTC_ADDRESS: '3PFo18vaPMSXFTt6zUDGk3UoPjD56QLXjh',
  // Stable Solana fixture wallet — also used by backend unit tests in
  // rotkehlchen/tests/unit/test_solana.py. Has a small SOL balance and no
  // SPL tokens, so account-add flow recordings stay tiny.
  // WARNING: avoid exercising transaction-history fetching against this
  // address (e.g. navigating to the history page while it is the tracked
  // account); it has ~1000+ signatures and would inflate the cassette.
  SOLANA_ADDRESS: 'updtkJ8HAhh3rSkBCd3p9Z1Q74yJW4rMhSbScRskDPM',
  KRAKEN_API_KEY: 'a39939bffed348299c6a859ca3f9a41e',
  KRAKEN_API_SECRET: '68203af4221446a08d156bb3a4fd27dc',
};
