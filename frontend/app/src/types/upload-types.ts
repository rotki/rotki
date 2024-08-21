import type { RuiIcons } from '@rotki/ui-library';
import type { Component } from 'vue';

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
  'bitstamp',
  'rotki_events',
  'rotki_trades',
  'bittrex',
  'kucoin',
  'blockpit',
] as const;

export type ImportSourceType = (typeof SOURCES)[number];

export interface ImportSource {
  key: string;
  label: string;
  logo?: string;
  icon?: RuiIcons;
  form: Component;
}
