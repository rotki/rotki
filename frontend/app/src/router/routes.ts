import type { RouteLocationRaw } from 'vue-router';

/**
 * Used to enforce the type of route
 * @param route
 */
function ensureRoute(route: RouteLocationRaw): RouteLocationRaw {
  return route;
}

export const Routes = {
  ACCOUNTS: ensureRoute('/accounts'),
  ACCOUNTS_BITCOIN: ensureRoute('/accounts/bitcoin'),
  ACCOUNTS_EVM: ensureRoute('/accounts/evm'),
  ACCOUNTS_SUBSTRATE: ensureRoute('/accounts/substrate'),
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
  BALANCES: ensureRoute('/balances'),
  BALANCES_BLOCKCHAIN: ensureRoute('/balances/blockchain'),
  BALANCES_EXCHANGE: ensureRoute('/balances/exchange'),
  BALANCES_MANUAL: ensureRoute('/balances/manual'),
  BALANCES_NON_FUNGIBLE: ensureRoute('/balances/non-fungible'),
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
    ACCOUNTS: {
      icon: 'lu-wallet' as const,
      route: Routes.ACCOUNTS,
      text: t('navigation_menu.accounts'),
    },
    ACCOUNTS_BITCOIN: {
      icon: 'lu-bitcoin-accounts' as const,
      route: Routes.ACCOUNTS_BITCOIN,
      text: t('navigation_menu.accounts_sub.bitcoin'),
    },
    ACCOUNTS_EVM: {
      icon: 'lu-evm-accounts' as const,
      route: Routes.ACCOUNTS_EVM,
      text: t('navigation_menu.accounts_sub.evm'),
    },
    ACCOUNTS_SUBSTRATE: {
      icon: 'lu-substrate-accounts' as const,
      route: Routes.ACCOUNTS_SUBSTRATE,
      text: t('navigation_menu.accounts_sub.substrate'),
    },
    ADDRESS_BOOK_MANAGER: {
      icon: 'lu-book-text' as const,
      route: Routes.ADDRESS_BOOK_MANAGER,
      text: t('navigation_menu.manage_address_book'),
    },
    API_KEYS: {
      icon: 'lu-key' as const,
      route: Routes.API_KEYS,
      text: t('navigation_menu.api_keys'),
    },
    API_KEYS_EXCHANGES: {
      icon: 'lu-coins-exchange' as const,
      route: Routes.API_KEYS_EXCHANGES,
      text: t('navigation_menu.api_keys_sub.exchanges'),
    },
    API_KEYS_EXTERNAL_SERVICES: {
      icon: 'lu-blocks' as const,
      route: Routes.API_KEYS_EXTERNAL_SERVICES,
      text: t('navigation_menu.api_keys_sub.external_services'),
    },
    API_KEYS_ROTKI_PREMIUM: {
      icon: 'lu-crown' as const,
      route: Routes.API_KEYS_ROTKI_PREMIUM,
      text: t('navigation_menu.api_keys_sub.premium'),
    },
    ASSET_MANAGER: {
      icon: 'lu-manage-assets' as const,
      route: Routes.ASSET_MANAGER,
      text: t('navigation_menu.manage_assets'),
    },
    ASSET_MANAGER_CEX_MAPPING: {
      icon: 'lu-scroll-text' as const,
      route: Routes.ASSET_MANAGER_CEX_MAPPING,
      text: t('navigation_menu.manage_assets_sub.cex_mapping'),
    },
    ASSET_MANAGER_CUSTOM: {
      icon: 'lu-custom-assets' as const,
      route: Routes.ASSET_MANAGER_CUSTOM,
      text: t('navigation_menu.manage_assets_sub.custom_assets'),
    },
    ASSET_MANAGER_MANAGED: {
      icon: 'lu-manage-assets' as const,
      route: Routes.ASSET_MANAGER_MANAGED,
      text: t('navigation_menu.manage_assets_sub.assets'),
    },
    ASSET_MANAGER_MORE: {
      icon: 'lu-more-assets' as const,
      route: Routes.ASSET_MANAGER_MORE,
      text: t('navigation_menu.manage_assets_sub.more'),
    },
    ASSET_MANAGER_NEWLY_DETECTED: {
      icon: 'lu-list-todo' as const,
      route: Routes.ASSET_MANAGER_NEWLY_DETECTED,
      text: t('navigation_menu.manage_assets_sub.newly_detected'),
    },
    ASSETS: {
      route: Routes.ASSETS,
      text: t('common.assets'),
    },
    BALANCES: {
      icon: 'lu-balances' as const,
      route: Routes.BALANCES,
      text: t('navigation_menu.balances'),
    },
    BALANCES_BLOCKCHAIN: {
      icon: 'lu-blockchain' as const,
      route: Routes.BALANCES_BLOCKCHAIN,
      text: t('navigation_menu.balances_sub.blockchain_balances'),
    },
    BALANCES_EXCHANGE: {
      icon: 'lu-coins-exchange' as const,
      route: Routes.BALANCES_EXCHANGE,
      text: t('navigation_menu.balances_sub.exchange_balances'),
    },
    BALANCES_MANUAL: {
      icon: 'lu-notebook-pen' as const,
      route: Routes.BALANCES_MANUAL,
      text: t('navigation_menu.balances_sub.manual_balances'),
    },
    BALANCES_NON_FUNGIBLE: {
      icon: 'lu-image' as const,
      route: Routes.BALANCES_NON_FUNGIBLE,
      text: t('navigation_menu.balances_sub.non_fungible_balances'),
    },
    CALENDAR: {
      icon: 'lu-calendar-days' as const,
      route: Routes.CALENDAR,
      text: t('navigation_menu.calendar'),
    },
    DASHBOARD: {
      icon: 'lu-layout-dashboard' as const,
      route: Routes.DASHBOARD,
      text: t('navigation_menu.dashboard'),
    },
    DEFI: {
      icon: 'lu-chart-line' as const,
      route: Routes.DEFI,
      text: t('navigation_menu.defi'),
    },
    DEFI_AIRDROPS: {
      icon: 'lu-gift' as const,
      route: Routes.DEFI_AIRDROPS,
      text: t('navigation_menu.defi_sub.airdrops'),
    },
    DEFI_DEPOSITS: {
      icon: 'lu-deposits' as const,
      route: Routes.DEFI_DEPOSITS,
      text: t('common.deposits'),
    },
    DEFI_DEPOSITS_LIQUIDITY: {
      icon: 'lu-droplets' as const,
      route: Routes.DEFI_DEPOSITS_LIQUIDITY,
      text: t('navigation_menu.defi_sub.deposits_sub.liquidity'),
    },
    DEFI_DEPOSITS_PROTOCOLS: {
      icon: 'lu-settings' as const,
      route: Routes.DEFI_DEPOSITS_PROTOCOLS,
      text: t('navigation_menu.defi_sub.deposits_sub.protocols'),
    },
    DEFI_LIABILITIES: {
      icon: 'lu-liabilities' as const,
      route: Routes.DEFI_LIABILITIES,
      text: t('navigation_menu.defi_sub.liabilities'),
    },
    DEFI_OVERVIEW: {
      icon: 'lu-square-kanban' as const,
      route: Routes.DEFI_OVERVIEW,
      text: t('navigation_menu.defi_sub.overview'),
    },
    HISTORY: {
      icon: 'lu-history' as const,
      route: Routes.HISTORY,
      text: t('navigation_menu.history'),
    },
    HISTORY_EVENTS: {
      icon: 'lu-history-events-fill' as const,
      route: Routes.HISTORY_EVENTS,
      text: t('navigation_menu.history_sub.history_events'),
    },
    HISTORY_TRADES: {
      icon: 'lu-shuffle' as const,
      route: Routes.HISTORY_TRADES,
      text: t('navigation_menu.history_sub.trades'),
    },
    IMPORT: {
      icon: 'lu-folder-input' as const,
      route: Routes.IMPORT,
      text: t('navigation_menu.import_data'),
    },
    LOCATIONS: {
      route: Routes.LOCATIONS,
      text: t('navigation_menu.locations'),
    },
    NFTS: {
      icon: 'lu-image' as const,
      route: Routes.NFTS,
      text: t('navigation_menu.nfts'),
    },
    PRICE_MANAGER: {
      icon: 'lu-manage-prices' as const,
      route: Routes.PRICE_MANAGER,
      text: t('navigation_menu.manage_prices'),
    },
    PRICE_MANAGER_HISTORIC: {
      icon: 'lu-historic-prices' as const,
      route: Routes.PRICE_MANAGER_HISTORIC,
      text: t('navigation_menu.manage_prices_sub.historic_prices'),
    },
    PRICE_MANAGER_LATEST: {
      icon: 'lu-latest-prices' as const,
      route: Routes.PRICE_MANAGER_LATEST,
      text: t('navigation_menu.manage_prices_sub.latest_prices'),
    },
    PROFIT_LOSS_REPORT: {
      icon: 'lu-calculator' as const,
      route: Routes.PROFIT_LOSS_REPORT,
      text: t('navigation_menu.profit_loss_report'),
    },
    PROFIT_LOSS_REPORTS: {
      icon: 'lu-calculator' as const,
      route: Routes.PROFIT_LOSS_REPORTS,
      text: t('navigation_menu.profit_loss_report'),
    },
    SETTINGS: {
      icon: 'lu-settings' as const,
      route: Routes.SETTINGS,
      text: t('navigation_menu.settings'),
    },
    SETTINGS_ACCOUNT: {
      icon: 'lu-user-round-cog' as const,
      route: Routes.SETTINGS_ACCOUNT,
      text: t('navigation_menu.settings_sub.account'),
    },
    SETTINGS_ACCOUNTING: {
      icon: 'lu-file-spreadsheet' as const,
      route: Routes.SETTINGS_ACCOUNTING,
      text: t('navigation_menu.settings_sub.accounting'),
    },
    SETTINGS_DATABASE: {
      icon: 'lu-manage-assets' as const,
      route: Routes.SETTINGS_DATABASE,
      text: t('navigation_menu.settings_sub.database'),
    },
    SETTINGS_GENERAL: {
      icon: 'lu-bolt' as const,
      route: Routes.SETTINGS_GENERAL,
      text: t('navigation_menu.settings_sub.general'),
    },
    SETTINGS_INTERFACE: {
      icon: 'lu-laptop-minimal' as const,
      route: Routes.SETTINGS_INTERFACE,
      text: t('navigation_menu.settings_sub.interface'),
    },
    SETTINGS_MODULES: {
      icon: 'lu-layout-grid' as const,
      route: Routes.SETTINGS_MODULES,
      text: t('navigation_menu.settings_sub.modules'),
    },
    SETTINGS_ORACLE: {
      icon: 'lu-circle-dollar-sign' as const,
      route: Routes.SETTINGS_ORACLE,
      text: t('navigation_menu.settings_sub.oracles'),
    },
    SETTINGS_RPC: {
      icon: 'lu-wifi' as const,
      route: Routes.SETTINGS_RPC,
      text: t('navigation_menu.settings_sub.rpc_nodes'),
    },
    STAKING: {
      icon: 'lu-layers' as const,
      route: Routes.STAKING,
      text: t('navigation_menu.staking'),
    },
    STATISTICS: {
      icon: 'lu-file-chart-column' as const,
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
