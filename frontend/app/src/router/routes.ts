import type { RouteLocationRaw } from 'vue-router';

/**
 * Used to enforce the type of route
 * @param route
 */
function ensureRoute(route: RouteLocationRaw): RouteLocationRaw {
  return route;
}

export const Routes = {
  ACCOUNTS_BALANCES: ensureRoute('/balances'),
  ACCOUNTS_BALANCES_BLOCKCHAIN: ensureRoute('/balances/blockchain'),
  ACCOUNTS_BALANCES_EXCHANGE: ensureRoute('/balances/exchange'),
  ACCOUNTS_BALANCES_MANUAL: ensureRoute('/balances/manual'),
  ACCOUNTS_BALANCES_NON_FUNGIBLE: ensureRoute('/balances/non-fungible'),
  ADDRESS_BOOK_MANAGER: ensureRoute('/address-book-manager'),
  API_KEYS: ensureRoute('/api-keys'),
  API_KEYS_EXCHANGES: ensureRoute('/api-keys/exchanges'),
  API_KEYS_EXTERNAL_SERVICES: ensureRoute('/api-keys/external'),
  API_KEYS_ROTKI_PREMIUM: ensureRoute('/api-keys/premium'),
  ASSET_MANAGER: ensureRoute('/asset-manager'),
  ASSET_MANAGER_CEX_MAPPING: ensureRoute('/asset-manager/more/cex-mapping'),
  ASSET_MANAGER_CUSTOM: ensureRoute('/asset-manager/custom'),
  ASSET_MANAGER_MANAGED: ensureRoute('/asset-manager/managed'),
  ASSET_MANAGER_MORE: ensureRoute('/asset-manager/more'),
  ASSET_MANAGER_NEWLY_DETECTED: ensureRoute('/asset-manager/more/newly-detected'),
  ASSETS: ensureRoute('/assets/:identifier'),
  CALENDAR: ensureRoute('/calendar'),
  DASHBOARD: ensureRoute('/dashboard'),
  DEFI: ensureRoute('/defi'),
  DEFI_AIRDROPS: ensureRoute('/defi/airdrops'),
  DEFI_DEPOSITS: ensureRoute('/defi/deposits'),
  DEFI_DEPOSITS_LIQUIDITY: ensureRoute('/defi/deposits/liquidity/:location*'),
  DEFI_DEPOSITS_PROTOCOLS: ensureRoute('/defi/deposits/protocols'),
  DEFI_LIABILITIES: ensureRoute('/defi/liabilities'),
  DEFI_OVERVIEW: ensureRoute('/defi/overview'),
  HISTORY: ensureRoute('/history'),
  HISTORY_EVENTS: ensureRoute('/history/transactions'),
  HISTORY_TRADES: ensureRoute('/history/trades'),
  IMPORT: ensureRoute('/import'),
  LOCATIONS: ensureRoute('/locations/:identifier'),
  NFTS: ensureRoute('/nfts'),
  PRICE_MANAGER: ensureRoute('/price-manager'),
  PRICE_MANAGER_HISTORIC: ensureRoute('/price-manager/historic'),
  PRICE_MANAGER_LATEST: ensureRoute('/price-manager/latest'),
  PROFIT_LOSS_REPORT: ensureRoute(`/reports/:id`),
  PROFIT_LOSS_REPORTS: ensureRoute('/reports/'),
  SETTINGS: ensureRoute('/settings'),
  SETTINGS_ACCOUNT: ensureRoute('/settings/account'),
  SETTINGS_ACCOUNTING: ensureRoute('/settings/accounting'),
  SETTINGS_DATABASE: ensureRoute('/settings/database'),
  SETTINGS_GENERAL: ensureRoute('/settings/general'),
  SETTINGS_INTERFACE: ensureRoute('/settings/interface'),
  SETTINGS_MODULES: ensureRoute('/settings/modules'),
  SETTINGS_ORACLE: ensureRoute('/settings/oracle'),
  SETTINGS_RPC: ensureRoute('/settings/rpc'),
  STAKING: ensureRoute('/staking/:location*'),
  STATISTICS: ensureRoute('/statistics'),
  STATISTICS_GRAPHS: ensureRoute('/statistics/graphs'),
  STATISTICS_HISTORY_EVENTS: ensureRoute('/statistics/history-events'),
  TAG_MANAGER: ensureRoute('/tag-manager'),
  USER_CREATE: ensureRoute('/user/create'),
  USER_LOGIN: ensureRoute('/user/login'),
} as const;

export const useAppRoutes = createSharedComposable(() => {
  const { t } = useI18n();
  const appRoutes = computed(() => ({
    ACCOUNTS_BALANCES: {
      icon: 'wallet-3-line' as const,
      route: Routes.ACCOUNTS_BALANCES,
      text: t('navigation_menu.accounts_balances'),
    },
    ACCOUNTS_BALANCES_BLOCKCHAIN: {
      icon: 'coins-line' as const,
      route: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
      text: t('navigation_menu.accounts_balances_sub.blockchain_balances'),
    },
    ACCOUNTS_BALANCES_EXCHANGE: {
      icon: 'exchange-line' as const,
      route: Routes.ACCOUNTS_BALANCES_EXCHANGE,
      text: t('navigation_menu.accounts_balances_sub.exchange_balances'),
    },
    ACCOUNTS_BALANCES_MANUAL: {
      icon: 'scales-line' as const,
      route: Routes.ACCOUNTS_BALANCES_MANUAL,
      text: t('navigation_menu.accounts_balances_sub.manual_balances'),
    },
    ACCOUNTS_BALANCES_NON_FUNGIBLE: {
      icon: 'scales-fill' as const,
      route: Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE,
      text: t('navigation_menu.accounts_balances_sub.non_fungible_balances'),
    },
    ADDRESS_BOOK_MANAGER: {
      icon: 'book-2-line' as const,
      route: Routes.ADDRESS_BOOK_MANAGER,
      text: t('navigation_menu.manage_address_book'),
    },
    API_KEYS: {
      icon: 'key-line' as const,
      route: Routes.API_KEYS,
      text: t('navigation_menu.api_keys'),
    },
    API_KEYS_EXCHANGES: {
      icon: 'swap-line' as const,
      route: Routes.API_KEYS_EXCHANGES,
      text: t('navigation_menu.api_keys_sub.exchanges'),
    },
    API_KEYS_EXTERNAL_SERVICES: {
      icon: 'links-line' as const,
      route: Routes.API_KEYS_EXTERNAL_SERVICES,
      text: t('navigation_menu.api_keys_sub.external_services'),
    },
    API_KEYS_ROTKI_PREMIUM: {
      icon: 'vip-crown-line' as const,
      route: Routes.API_KEYS_ROTKI_PREMIUM,
      text: t('navigation_menu.api_keys_sub.premium'),
    },
    ASSET_MANAGER: {
      icon: 'database-2-line' as const,
      route: Routes.ASSET_MANAGER,
      text: t('navigation_menu.manage_assets'),
    },
    ASSET_MANAGER_CEX_MAPPING: {
      icon: 'file-list-3-line' as const,
      route: Routes.ASSET_MANAGER_CEX_MAPPING,
      text: t('navigation_menu.manage_assets_sub.cex_mapping'),
    },
    ASSET_MANAGER_CUSTOM: {
      icon: 'database-line' as const,
      route: Routes.ASSET_MANAGER_CUSTOM,
      text: t('navigation_menu.manage_assets_sub.custom_assets'),
    },
    ASSET_MANAGER_MANAGED: {
      icon: 'server-line' as const,
      route: Routes.ASSET_MANAGER_MANAGED,
      text: t('navigation_menu.manage_assets_sub.assets'),
    },
    ASSET_MANAGER_MORE: {
      icon: 'expand-right-line' as const,
      route: Routes.ASSET_MANAGER_MORE,
      text: t('navigation_menu.manage_assets_sub.more'),
    },
    ASSET_MANAGER_NEWLY_DETECTED: {
      icon: 'list-radio' as const,
      route: Routes.ASSET_MANAGER_NEWLY_DETECTED,
      text: t('navigation_menu.manage_assets_sub.newly_detected'),
    },
    ASSETS: {
      route: Routes.ASSETS,
      text: t('common.assets'),
    },
    CALENDAR: {
      icon: 'calendar-todo-line' as const,
      route: Routes.CALENDAR,
      text: t('navigation_menu.calendar'),
    },
    DASHBOARD: {
      icon: 'dashboard-line' as const,
      route: Routes.DASHBOARD,
      text: t('navigation_menu.dashboard'),
    },
    DEFI: {
      icon: 'line-chart-line' as const,
      route: Routes.DEFI,
      text: t('navigation_menu.defi'),
    },
    DEFI_AIRDROPS: {
      icon: 'gift-line' as const,
      route: Routes.DEFI_AIRDROPS,
      text: t('navigation_menu.defi_sub.airdrops'),
    },
    DEFI_DEPOSITS: {
      icon: 'login-circle-line' as const,
      route: Routes.DEFI_DEPOSITS,
      text: t('common.deposits'),
    },
    DEFI_DEPOSITS_LIQUIDITY: {
      icon: 'water-percent-line' as const,
      route: Routes.DEFI_DEPOSITS_LIQUIDITY,
      text: t('navigation_menu.defi_sub.deposits_sub.liquidity'),
    },
    DEFI_DEPOSITS_PROTOCOLS: {
      icon: 'settings-2-line' as const,
      route: Routes.DEFI_DEPOSITS_PROTOCOLS,
      text: t('navigation_menu.defi_sub.deposits_sub.protocols'),
    },
    DEFI_LIABILITIES: {
      icon: 'logout-circle-r-line' as const,
      route: Routes.DEFI_LIABILITIES,
      text: t('navigation_menu.defi_sub.liabilities'),
    },
    DEFI_OVERVIEW: {
      icon: 'bar-chart-box-line' as const,
      route: Routes.DEFI_OVERVIEW,
      text: t('navigation_menu.defi_sub.overview'),
    },
    HISTORY: {
      icon: 'history-line' as const,
      route: Routes.HISTORY,
      text: t('navigation_menu.history'),
    },
    HISTORY_EVENTS: {
      icon: 'exchange-box-line' as const,
      route: Routes.HISTORY_EVENTS,
      text: t('navigation_menu.history_sub.history_events'),
    },
    HISTORY_TRADES: {
      icon: 'shuffle-line' as const,
      route: Routes.HISTORY_TRADES,
      text: t('navigation_menu.history_sub.trades'),
    },
    IMPORT: {
      icon: 'folder-received-line' as const,
      route: Routes.IMPORT,
      text: t('navigation_menu.import_data'),
    },
    LOCATIONS: {
      route: Routes.LOCATIONS,
      text: t('navigation_menu.locations'),
    },
    NFTS: {
      icon: 'image-line' as const,
      route: Routes.NFTS,
      text: t('navigation_menu.nfts'),
    },
    PRICE_MANAGER: {
      icon: 'file-chart-line' as const,
      route: Routes.PRICE_MANAGER,
      text: t('navigation_menu.manage_prices'),
    },
    PRICE_MANAGER_HISTORIC: {
      icon: 'calendar-2-line' as const,
      route: Routes.PRICE_MANAGER_HISTORIC,
      text: t('navigation_menu.manage_prices_sub.historic_prices'),
    },
    PRICE_MANAGER_LATEST: {
      icon: 'calendar-event-line' as const,
      route: Routes.PRICE_MANAGER_LATEST,
      text: t('navigation_menu.manage_prices_sub.latest_prices'),
    },
    PROFIT_LOSS_REPORT: {
      icon: 'calculator-line' as const,
      route: Routes.PROFIT_LOSS_REPORT,
      text: t('navigation_menu.profit_loss_report'),
    },
    PROFIT_LOSS_REPORTS: {
      icon: 'calculator-line' as const,
      route: Routes.PROFIT_LOSS_REPORTS,
      text: t('navigation_menu.profit_loss_report'),
    },
    SETTINGS: {
      icon: 'settings-4-fill' as const,
      route: Routes.SETTINGS,
      text: t('navigation_menu.settings'),
    },
    SETTINGS_ACCOUNT: {
      icon: 'admin-line' as const,
      route: Routes.SETTINGS_ACCOUNT,
      text: t('navigation_menu.settings_sub.account'),
    },
    SETTINGS_ACCOUNTING: {
      icon: 'contacts-line' as const,
      route: Routes.SETTINGS_ACCOUNTING,
      text: t('navigation_menu.settings_sub.accounting'),
    },
    SETTINGS_DATABASE: {
      icon: 'database-2-line' as const,
      route: Routes.SETTINGS_DATABASE,
      text: t('navigation_menu.settings_sub.database'),
    },
    SETTINGS_GENERAL: {
      icon: 'user-settings-line' as const,
      route: Routes.SETTINGS_GENERAL,
      text: t('navigation_menu.settings_sub.general'),
    },
    SETTINGS_INTERFACE: {
      icon: 'macbook-line' as const,
      route: Routes.SETTINGS_INTERFACE,
      text: t('navigation_menu.settings_sub.interface'),
    },
    SETTINGS_MODULES: {
      icon: 'layout-grid-line' as const,
      route: Routes.SETTINGS_MODULES,
      text: t('navigation_menu.settings_sub.modules'),
    },
    SETTINGS_ORACLE: {
      icon: 'exchange-dollar-line' as const,
      route: Routes.SETTINGS_ORACLE,
      text: t('navigation_menu.settings_sub.oracles'),
    },
    SETTINGS_RPC: {
      icon: 'wifi-line' as const,
      route: Routes.SETTINGS_RPC,
      text: t('navigation_menu.settings_sub.rpc_nodes'),
    },
    STAKING: {
      icon: 'inbox-archive-line' as const,
      route: Routes.STAKING,
      text: t('navigation_menu.staking'),
    },
    STATISTICS: {
      icon: 'file-chart-line' as const,
      route: Routes.STATISTICS,
      text: t('navigation_menu.statistics'),
    },
    STATISTICS_GRAPHS: {
      icon: 'lu-chart-line' as const,
      route: Routes.STATISTICS_GRAPHS,
      text: t('navigation_menu.statistics_sub.graphs'),
    },
    STATISTICS_HISTORY_EVENTS: {
      icon: 'lu-chart-bar' as const,
      route: Routes.STATISTICS_HISTORY_EVENTS,
      text: t('navigation_menu.statistics_sub.history_events'),
    },
    TAG_MANAGER: {
      icon: 'lu-tag-manager' as const,
      route: Routes.TAG_MANAGER,
      text: t('navigation_menu.tag_manager'),
    },
  } as const));

  return {
    appRoutes,
  };
});
