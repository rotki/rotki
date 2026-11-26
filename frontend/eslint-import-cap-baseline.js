/**
 * Files over the 20-import cap only because the Vue, VueUse, Pinia, router and i18n APIs are
 * imported explicitly since auto-imports were removed.
 *
 * @remarks
 * A baseline to work down: each file should be split back under 20 and then dropped from here.
 * They are held at 26, the most any of them has, so none can grow further. Do not add files.
 * Brackets in page paths are escaped, since flat config reads these as globs.
 */
export const importCapBaseline = [
  'app/src/modules/accounts/AccountBalances.vue',
  'app/src/modules/accounts/details/AccountDetailsDrawer.vue',
  'app/src/modules/accounts/manual-balances/ManualBalanceTable.vue',
  'app/src/modules/accounts/table/AccountBalancesTable.vue',
  'app/src/modules/assets/admin/managed/ManagedAssetForm.vue',
  'app/src/modules/assets/prices/components/oracle/OracleCacheContent.vue',
  'app/src/modules/assets/prices/components/oracle/OraclePriceContent.vue',
  'app/src/modules/assets/prices/historic/HistoricPriceContent.vue',
  'app/src/modules/assets/prices/latest/LatestPriceContent.vue',
  'app/src/modules/auth/login/LoginForm.vue',
  'app/src/modules/balances/AssetBalances.vue',
  'app/src/modules/balances/components/BalanceViewPanel.vue',
  'app/src/modules/balances/use-aggregated-balances.ts',
  'app/src/modules/core/table/use-server-table.ts',
  'app/src/modules/dashboard/DashboardAssetTable.vue',
  'app/src/modules/dashboard/OverallBalances.vue',
  'app/src/modules/dashboard/liquidity-pools/PoolTable.vue',
  'app/src/modules/dashboard/snapshots/components/SnapshotBalancesTable.vue',
  'app/src/modules/history/data-issues/DataIssuesView.vue',
  'app/src/modules/history/data-issues/components/DataIssueDetailContent.vue',
  'app/src/modules/history/data-issues/components/DataIssuesPanelContent.vue',
  'app/src/modules/history/events/HistoryEventsView.vue',
  'app/src/modules/history/events/actions-center/use-history-event-issues.ts',
  'app/src/modules/history/events/use-history-events-data.ts',
  'app/src/modules/history/events/use-history-events-filters.ts',
  'app/src/modules/history/events/use-unmatched-asset-movements.ts',
  'app/src/modules/history/events/use-unmatched-bridge-transactions.ts',
  'app/src/modules/integrations/gnosis-pay/components/GnosisPayAuth.vue',
  'app/src/modules/locations/components/LocationManager.vue',
  'app/src/modules/reports/ProfitLossEvents.vue',
  'app/src/modules/settings/api-keys/exchange/ExchangeKeysForm.vue',
  'app/src/modules/shell/action-center/use-global-action-center.ts',
  'app/src/modules/shell/action-center/use-integration-rows.ts',
  'app/src/modules/statistics/pricing/use-backfill-requests.ts',
  'app/src/modules/user-data/ImportSource.vue',
  'app/src/modules/wallet/send/TradeSendCard.vue',
  'app/src/pages/accounts/evm/\\[\\[tab\\]\\].vue',
  'app/src/pages/assets/\\[identifier\\].vue',
  'app/src/pages/balances/banks/index.vue',
  'app/src/pages/balances/exchange/\\[\\[exchange\\]\\].vue',
  'app/src/pages/balances/manual/\\[\\[tab\\]\\].vue',
  'app/src/pages/statistics/snapshots/\\[timestamp\\].vue',
  'app/src/pages/user/login/index.vue',
];
