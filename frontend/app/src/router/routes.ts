import type { RouteLocationRaw } from 'vue-router';

/**
 * Used to enforce the type of route
 * @param route
 */
function ensureRoute(route: RouteLocationRaw): RouteLocationRaw {
  return route;
}

export const Routes = {
  DASHBOARD: ensureRoute('/dashboard'),
  USER_LOGIN: ensureRoute('/user/login'),
  USER_CREATE: ensureRoute('/user/create'),
  ACCOUNTS_BALANCES: ensureRoute('/balances'),
  ACCOUNTS_BALANCES_BLOCKCHAIN: ensureRoute('/balances/blockchain'),
  ACCOUNTS_BALANCES_EXCHANGE: ensureRoute('/balances/exchange'),
  ACCOUNTS_BALANCES_MANUAL: ensureRoute('/balances/manual'),
  ACCOUNTS_BALANCES_NON_FUNGIBLE: ensureRoute('/balances/non-fungible'),
  NFTS: ensureRoute('/nfts'),
  HISTORY: ensureRoute('/history'),
  HISTORY_TRADES: ensureRoute('/history/trades'),
  HISTORY_DEPOSITS_WITHDRAWALS: ensureRoute('/history/deposits-withdrawals'),
  HISTORY_EVENTS: ensureRoute('/history/transactions'),
  DEFI: ensureRoute('/defi'),
  DEFI_OVERVIEW: ensureRoute('/defi/overview'),
  DEFI_DEPOSITS: ensureRoute('/defi/deposits'),
  DEFI_LIABILITIES: ensureRoute('/defi/liabilities'),
  DEFI_DEPOSITS_PROTOCOLS: ensureRoute('/defi/deposits/protocols'),
  DEFI_DEPOSITS_LIQUIDITY: ensureRoute('/defi/deposits/liquidity/:location*'),
  DEFI_AIRDROPS: ensureRoute('/defi/airdrops'),
  STATISTICS: ensureRoute('/statistics'),
  STAKING: ensureRoute('/staking/:location*'),
  PROFIT_LOSS_REPORTS: ensureRoute('/reports/'),
  PROFIT_LOSS_REPORT: ensureRoute(`/reports/:id`),
  ASSET_MANAGER: ensureRoute('/asset-manager'),
  ASSET_MANAGER_MANAGED: ensureRoute('/asset-manager/managed'),
  ASSET_MANAGER_CUSTOM: ensureRoute('/asset-manager/custom'),
  ASSET_MANAGER_MORE: ensureRoute('/asset-manager/more'),
  ASSET_MANAGER_NEWLY_DETECTED: ensureRoute('/asset-manager/more/newly-detected'),
  ASSET_MANAGER_CEX_MAPPING: ensureRoute('/asset-manager/more/cex-mapping'),
  PRICE_MANAGER: ensureRoute('/price-manager'),
  PRICE_MANAGER_LATEST: ensureRoute('/price-manager/latest'),
  PRICE_MANAGER_HISTORIC: ensureRoute('/price-manager/historic'),
  ADDRESS_BOOK_MANAGER: ensureRoute('/address-book-manager'),
  API_KEYS: ensureRoute('/api-keys'),
  API_KEYS_ROTKI_PREMIUM: ensureRoute('/api-keys/premium'),
  API_KEYS_EXCHANGES: ensureRoute('/api-keys/exchanges'),
  API_KEYS_EXTERNAL_SERVICES: ensureRoute('/api-keys/external'),
  IMPORT: ensureRoute('/import'),
  SETTINGS: ensureRoute('/settings'),
  SETTINGS_GENERAL: ensureRoute('/settings/general'),
  SETTINGS_ACCOUNTING: ensureRoute('/settings/accounting'),
  SETTINGS_DATA_SECURITY: ensureRoute('/settings/data-security'),
  SETTINGS_MODULES: ensureRoute('/settings/modules'),
  ASSETS: ensureRoute('/assets/:identifier'),
  LOCATIONS: ensureRoute('/locations/:identifier'),
  CALENDAR: ensureRoute('/calendar'),
} as const;

export const useAppRoutes = createSharedComposable(() => {
  const { t } = useI18n();
  const appRoutes = computed(() => ({
    DASHBOARD: {
      route: Routes.DASHBOARD,
      icon: 'dashboard-line' as const,
      text: t('navigation_menu.dashboard'),
    },
    ACCOUNTS_BALANCES: {
      route: Routes.ACCOUNTS_BALANCES,
      icon: 'wallet-3-line' as const,
      text: t('navigation_menu.accounts_balances'),
    },
    ACCOUNTS_BALANCES_BLOCKCHAIN: {
      route: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
      icon: 'coins-line' as const,
      text: t('navigation_menu.accounts_balances_sub.blockchain_balances'),
    },
    ACCOUNTS_BALANCES_EXCHANGE: {
      route: Routes.ACCOUNTS_BALANCES_EXCHANGE,
      icon: 'exchange-line' as const,
      text: t('navigation_menu.accounts_balances_sub.exchange_balances'),
    },
    ACCOUNTS_BALANCES_MANUAL: {
      route: Routes.ACCOUNTS_BALANCES_MANUAL,
      icon: 'scales-line' as const,
      text: t('navigation_menu.accounts_balances_sub.manual_balances'),
    },
    ACCOUNTS_BALANCES_NON_FUNGIBLE: {
      route: Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE,
      icon: 'scales-fill' as const,
      text: t('navigation_menu.accounts_balances_sub.non_fungible_balances'),
    },
    NFTS: {
      route: Routes.NFTS,
      icon: 'image-line' as const,
      text: t('navigation_menu.nfts'),
    },
    HISTORY: {
      route: Routes.HISTORY,
      icon: 'history-line' as const,
      text: t('navigation_menu.history'),
    },
    HISTORY_TRADES: {
      route: Routes.HISTORY_TRADES,
      icon: 'shuffle-line' as const,
      text: t('navigation_menu.history_sub.trades'),
    },
    HISTORY_DEPOSITS_WITHDRAWALS: {
      route: Routes.HISTORY_DEPOSITS_WITHDRAWALS,
      icon: 'bank-line' as const,
      text: t('navigation_menu.history_sub.deposits_withdrawals'),
    },
    HISTORY_EVENTS: {
      route: Routes.HISTORY_EVENTS,
      icon: 'exchange-box-line' as const,
      text: t('navigation_menu.history_sub.history_events'),
    },
    DEFI: {
      route: Routes.DEFI,
      icon: 'line-chart-line' as const,
      text: t('navigation_menu.defi'),
    },
    DEFI_OVERVIEW: {
      route: Routes.DEFI_OVERVIEW,
      icon: 'bar-chart-box-line' as const,
      text: t('navigation_menu.defi_sub.overview'),
    },
    DEFI_DEPOSITS: {
      route: Routes.DEFI_DEPOSITS,
      icon: 'login-circle-line' as const,
      text: t('common.deposits'),
    },
    DEFI_LIABILITIES: {
      route: Routes.DEFI_LIABILITIES,
      icon: 'logout-circle-r-line' as const,
      text: t('navigation_menu.defi_sub.liabilities'),
    },
    DEFI_DEPOSITS_PROTOCOLS: {
      route: Routes.DEFI_DEPOSITS_PROTOCOLS,
      icon: 'settings-2-line' as const,
      text: t('navigation_menu.defi_sub.deposits_sub.protocols'),
    },
    DEFI_DEPOSITS_LIQUIDITY: {
      route: Routes.DEFI_DEPOSITS_LIQUIDITY,
      icon: 'water-percent-line' as const,
      text: t('navigation_menu.defi_sub.deposits_sub.liquidity'),
    },
    DEFI_AIRDROPS: {
      route: Routes.DEFI_AIRDROPS,
      icon: 'gift-line' as const,
      text: t('navigation_menu.defi_sub.airdrops'),
    },
    STATISTICS: {
      route: Routes.STATISTICS,
      icon: 'file-chart-line' as const,
      text: t('navigation_menu.statistics'),
    },
    STAKING: {
      route: Routes.STAKING,
      icon: 'inbox-archive-line' as const,
      text: t('navigation_menu.staking'),
    },
    PROFIT_LOSS_REPORTS: {
      route: Routes.PROFIT_LOSS_REPORTS,
      icon: 'calculator-line' as const,
      text: t('navigation_menu.profit_loss_report'),
    },
    PROFIT_LOSS_REPORT: {
      route: Routes.PROFIT_LOSS_REPORT,
      icon: 'calculator-line' as const,
      text: t('navigation_menu.profit_loss_report'),
    },
    ASSET_MANAGER: {
      route: Routes.ASSET_MANAGER,
      icon: 'database-2-line' as const,
      text: t('navigation_menu.manage_assets'),
    },
    ASSET_MANAGER_MANAGED: {
      route: Routes.ASSET_MANAGER_MANAGED,
      icon: 'server-line' as const,
      text: t('navigation_menu.manage_assets_sub.assets'),
    },
    ASSET_MANAGER_CUSTOM: {
      route: Routes.ASSET_MANAGER_CUSTOM,
      icon: 'database-line' as const,
      text: t('navigation_menu.manage_assets_sub.custom_assets'),
    },
    ASSET_MANAGER_MORE: {
      route: Routes.ASSET_MANAGER_MORE,
      icon: 'expand-right-line' as const,
      text: t('navigation_menu.manage_assets_sub.more'),
    },
    ASSET_MANAGER_NEWLY_DETECTED: {
      route: Routes.ASSET_MANAGER_NEWLY_DETECTED,
      icon: 'list-radio' as const,
      text: t('navigation_menu.manage_assets_sub.newly_detected'),
    },
    ASSET_MANAGER_CEX_MAPPING: {
      route: Routes.ASSET_MANAGER_CEX_MAPPING,
      icon: 'file-list-3-line' as const,
      text: t('navigation_menu.manage_assets_sub.cex_mapping'),
    },
    PRICE_MANAGER: {
      route: Routes.PRICE_MANAGER,
      icon: 'file-chart-line' as const,
      text: t('navigation_menu.manage_prices'),
    },
    PRICE_MANAGER_LATEST: {
      route: Routes.PRICE_MANAGER_LATEST,
      icon: 'calendar-event-line' as const,
      text: t('navigation_menu.manage_prices_sub.latest_prices'),
    },
    PRICE_MANAGER_HISTORIC: {
      route: Routes.PRICE_MANAGER_HISTORIC,
      icon: 'calendar-2-line' as const,
      text: t('navigation_menu.manage_prices_sub.historic_prices'),
    },
    ADDRESS_BOOK_MANAGER: {
      route: Routes.ADDRESS_BOOK_MANAGER,
      icon: 'book-2-line' as const,
      text: t('navigation_menu.manage_address_book'),
    },
    API_KEYS: {
      route: Routes.API_KEYS,
      icon: 'key-line' as const,
      text: t('navigation_menu.api_keys'),
    },
    API_KEYS_ROTKI_PREMIUM: {
      route: Routes.API_KEYS_ROTKI_PREMIUM,
      icon: 'vip-crown-line' as const,
      text: t('navigation_menu.api_keys_sub.premium'),
    },
    API_KEYS_EXCHANGES: {
      route: Routes.API_KEYS_EXCHANGES,
      icon: 'swap-line' as const,
      text: t('navigation_menu.api_keys_sub.exchanges'),
    },
    API_KEYS_EXTERNAL_SERVICES: {
      route: Routes.API_KEYS_EXTERNAL_SERVICES,
      icon: 'links-line' as const,
      text: t('navigation_menu.api_keys_sub.external_services'),
    },
    IMPORT: {
      route: Routes.IMPORT,
      icon: 'folder-received-line' as const,
      text: t('navigation_menu.import_data'),
    },
    SETTINGS: {
      route: Routes.SETTINGS,
      icon: 'settings-4-fill' as const,
      text: t('navigation_menu.settings'),
    },
    SETTINGS_GENERAL: {
      route: Routes.SETTINGS_GENERAL,
      icon: 'user-settings-line' as const,
      text: t('navigation_menu.settings_sub.general'),
    },
    SETTINGS_ACCOUNTING: {
      route: Routes.SETTINGS_ACCOUNTING,
      icon: 'contacts-line' as const,
      text: t('navigation_menu.settings_sub.accounting'),
    },
    SETTINGS_DATA_SECURITY: {
      route: Routes.SETTINGS_DATA_SECURITY,
      icon: 'admin-line' as const,
      text: t('navigation_menu.settings_sub.data_security'),
    },
    SETTINGS_MODULES: {
      route: Routes.SETTINGS_MODULES,
      icon: 'layout-grid-line' as const,
      text: t('navigation_menu.settings_sub.modules'),
    },
    ASSETS: {
      route: Routes.ASSETS,
      text: t('common.assets'),
    },
    LOCATIONS: {
      route: Routes.LOCATIONS,
      text: t('navigation_menu.locations'),
    },
    CALENDAR: {
      route: Routes.CALENDAR,
      icon: 'calendar-todo-line' as const,
      text: t('navigation_menu.calendar'),
    },
  } as const));

  return {
    appRoutes,
  };
});
