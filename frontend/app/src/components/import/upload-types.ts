export const SOURCES = [
  'cointracking.info',
  'cryptocom',
  'icon',
  'zip',
  'csv',
  'json',
  'nexo',
  'blockfi-transactions',
  'blockfi-trades',
  'shapeshift-trades',
  'uphold',
  'bisq',
  'binance'
] as const;

export type ImportSourceType = typeof SOURCES[number];
