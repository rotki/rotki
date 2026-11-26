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
  'app/src/modules/accounts/details/AccountDetailsDrawer.vue',
  'app/src/modules/accounts/table/AccountBalancesTable.vue',
  'app/src/modules/assets/admin/managed/ManagedAssetForm.vue',
  'app/src/modules/auth/login/LoginForm.vue',
  'app/src/modules/dashboard/DashboardAssetTable.vue',
  'app/src/modules/dashboard/snapshots/components/SnapshotBalancesTable.vue',
  'app/src/modules/history/data-issues/DataIssuesView.vue',
  'app/src/modules/history/data-issues/components/DataIssuesPanelContent.vue',
  'app/src/modules/history/events/HistoryEventsView.vue',
  'app/src/modules/integrations/gnosis-pay/components/GnosisPayAuth.vue',
  'app/src/modules/locations/components/LocationManager.vue',
  'app/src/modules/wallet/send/TradeSendCard.vue',
  'app/src/pages/statistics/snapshots/\\[timestamp\\].vue',
  'app/src/pages/user/login/index.vue',
];
