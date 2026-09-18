import type { BalanceSource } from '@/modules/balances/refresh/core/refresh-types';

export const DashboardRefreshKind = {
  BALANCES: 'balances',
  EXTRA_SOURCE: 'extra-source',
  PRICES: 'prices',
  REDETECT: 'redetect',
  SOURCE: 'source',
} as const;

/**
 * Dashboard tables with a query of their own, outside the balance sources: they refresh on their own
 * and bring their own values, so no price refresh follows them.
 */
export const DashboardExtraSource = {
  NFTS: 'nfts',
  POOLS: 'pools',
} as const;

export type DashboardExtraSource = (typeof DashboardExtraSource)[keyof typeof DashboardExtraSource];

/** What the dashboard refresh button was asked to do. */
export type DashboardRefreshAction =
  | { readonly kind: typeof DashboardRefreshKind.BALANCES }
  | { readonly kind: typeof DashboardRefreshKind.REDETECT }
  | { readonly kind: typeof DashboardRefreshKind.PRICES }
  | { readonly kind: typeof DashboardRefreshKind.SOURCE; readonly source: BalanceSource }
  | { readonly kind: typeof DashboardRefreshKind.EXTRA_SOURCE; readonly source: DashboardExtraSource };
