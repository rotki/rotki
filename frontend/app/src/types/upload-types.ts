export const SOURCES = [
  'cointracking',
  'cryptocom',
  'icon',
  'zip',
  'csv',
  'json',
  'nexo',
  'blockfi_transactions',
  'blockfi_trades',
  'shapeshift_trades',
  'uphold_transactions',
  'bisq_trades',
  'binance',
  'bitcoin_tax',
  'bitmex_wallet_history',
  'rotki_events',
  'rotki_trades'
] as const;

export type ImportSourceType = (typeof SOURCES)[number];
