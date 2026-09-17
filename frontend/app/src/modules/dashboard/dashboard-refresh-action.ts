import type { BalanceSource } from '@/modules/balances/refresh/core/refresh-types';

export const DashboardRefreshKind = {
  BALANCES: 'balances',
  PRICES: 'prices',
  REDETECT: 'redetect',
  SOURCE: 'source',
} as const;

/** What the dashboard refresh button was asked to do. */
export type DashboardRefreshAction =
  | { readonly kind: typeof DashboardRefreshKind.BALANCES }
  | { readonly kind: typeof DashboardRefreshKind.REDETECT }
  | { readonly kind: typeof DashboardRefreshKind.PRICES }
  | { readonly kind: typeof DashboardRefreshKind.SOURCE; readonly source: BalanceSource };
