export const Routes: Record<string, string> = {
  ROOT: '/',
  DASHBOARD: '/dashboard',
  USER: '/user',
  USER_LOGIN: '/user/login',
  USER_CREATE: '/user/create',
  ACCOUNTS_BALANCES: '/accounts-balances',
  ACCOUNTS_BALANCES_BLOCKCHAIN: '/accounts-balances/blockchain-balances',
  ACCOUNTS_BALANCES_EXCHANGE: '/accounts-balances/exchange-balances',
  ACCOUNTS_BALANCES_MANUAL: '/accounts-balances/manual-balances',
  ACCOUNTS_BALANCES_NON_FUNGIBLE: '/accounts-balances/nonfungible',
  NFTS: '/nfts',
  HISTORY: '/history',
  HISTORY_TRADES: '/history/trades',
  HISTORY_DEPOSITS_WITHDRAWALS: '/history/deposits-withdrawals',
  HISTORY_EVENTS: '/history/transactions',
  DEFI: '/defi',
  DEFI_OVERVIEW: '/defi/overview',
  DEFI_DEPOSITS: '/defi/deposits',
  DEFI_LIABILITIES: '/defi/liabilities',
  DEFI_DEPOSITS_PROTOCOLS: '/defi/deposits/protocols',
  DEFI_DEPOSITS_LIQUIDITY: '/defi/deposits/liquidity/:location*',
  DEFI_AIRDROPS: '/defi/airdrops',
  STATISTICS: '/statistics',
  STAKING: '/staking/:location*',
  PROFIT_LOSS_REPORTS: '/reports/',
  PROFIT_LOSS_REPORT: `/reports/:id`,
  ASSET_MANAGER: '/asset-manager',
  ASSET_MANAGER_MANAGED: '/asset-manager/managed',
  ASSET_MANAGER_CUSTOM: '/asset-manager/custom',
  ASSET_MANAGER_MORE: '/asset-manager/more',
  ASSET_MANAGER_NEWLY_DETECTED: '/asset-manager/more/newly-added',
  ASSET_MANAGER_CEX_MAPPING: '/asset-manager/more/cex-mapping',
  PRICE_MANAGER: '/price-manager',
  PRICE_MANAGER_LATEST: '/price-manager/latest',
  PRICE_MANAGER_HISTORIC: '/price-manager/historic',
  ADDRESS_BOOK_MANAGER: '/address-book-manager',
  API_KEYS: '/settings/api-keys',
  API_KEYS_ROTKI_PREMIUM: '/settings/api-keys/rotki-premium',
  API_KEYS_EXCHANGES: '/settings/api-keys/exchanges',
  API_KEYS_EXTERNAL_SERVICES: '/settings/api-keys/external-services',
  IMPORT: '/import',
  SETTINGS: '/settings',
  SETTINGS_GENERAL: '/settings/general',
  SETTINGS_ACCOUNTING: '/settings/accounting',
  SETTINGS_DATA_SECURITY: '/settings/data-security',
  SETTINGS_MODULES: '/settings/modules',
  ASSETS: '/assets/:identifier',
  LOCATIONS: '/locations/:identifier',
  CALENDAR: '/calendar',
};

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
  }));

  return {
    appRoutes,
  };
});
