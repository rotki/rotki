enum RouteNames {
  ROOT = 'ROOT',
  USER = 'USER',
  USER_LOGIN = 'USER_LOGIN',
  USER_CREATE = 'USER_CREATE',
  DASHBOARD = 'DASHBOARD',
  ACCOUNTS_BALANCES = 'ACCOUNTS_BALANCES',
  ACCOUNTS_BALANCES_BLOCKCHAIN = 'ACCOUNTS_BALANCES_BLOCKCHAIN',
  ACCOUNTS_BALANCES_EXCHANGE = 'ACCOUNTS_BALANCES_EXCHANGE',
  ACCOUNTS_BALANCES_MANUAL = 'ACCOUNTS_BALANCES_MANUAL',
  ACCOUNTS_BALANCES_NON_FUNGIBLE = 'ACCOUNTS_BALANCES_NON_FUNGIBLE',
  NFTS = 'NFTS',
  HISTORY = 'HISTORY',
  HISTORY_TRADES = 'HISTORY_TRADES',
  HISTORY_DEPOSITS_WITHDRAWALS = 'HISTORY_DEPOSITS_WITHDRAWALS',
  HISTORY_EVENTS = 'HISTORY_EVENTS',
  DEFI = 'DEFI',
  DEFI_OVERVIEW = 'DEFI_OVERVIEW',
  DEFI_DEPOSITS = 'DEFI_DEPOSITS',
  DEFI_LIABILITIES = 'DEFI_LIABILITIES',
  DEFI_DEPOSITS_PROTOCOLS = 'DEFI_DEPOSITS_PROTOCOLS',
  DEFI_DEPOSITS_LIQUIDITY = 'DEFI_DEPOSITS_LIQUIDITY',
  DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2 = 'DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2',
  DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3 = 'DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3',
  DEFI_DEPOSITS_LIQUIDITY_BALANCER = 'DEFI_DEPOSITS_LIQUIDITY_BALANCER',
  DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP = 'DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP',
  DEFI_AIRDROPS = 'DEFI_AIRDROPS',
  STATISTICS = 'STATISTICS',
  STAKING = 'STAKING',
  PROFIT_LOSS_REPORTS = 'PROFIT_LOSS_REPORTS',
  PROFIT_LOSS_REPORT = 'PROFIT_LOSS_REPORT',
  ASSET_MANAGER = 'ASSET_MANAGER',
  ASSET_MANAGER_MANAGED = 'ASSET_MANAGER_MANAGED',
  ASSET_MANAGER_CUSTOM = 'ASSET_MANAGER_CUSTOM',
  ASSET_MANAGER_NEWLY_DETECTED = 'ASSET_MANAGER_NEWLY_DETECTED',
  PRICE_MANAGER = 'PRICE_MANAGER',
  PRICE_MANAGER_LATEST = 'PRICE_MANAGER_LATEST',
  PRICE_MANAGER_HISTORIC = 'PRICE_MANAGER_HISTORIC',
  ADDRESS_BOOK_MANAGER = 'ADDRESS_BOOK_MANAGER',
  API_KEYS = 'API_KEYS',
  API_KEYS_ROTKI_PREMIUM = 'API_KEYS_ROTKI_PREMIUM',
  API_KEYS_EXCHANGES = 'API_KEYS_EXCHANGES',
  API_KEYS_EXTERNAL_SERVICES = 'API_KEYS_EXTERNAL_SERVICES',
  IMPORT = 'IMPORT',
  SETTINGS = 'SETTINGS',
  SETTINGS_GENERAL = 'SETTINGS_GENERAL',
  SETTINGS_ACCOUNTING = 'SETTINGS_ACCOUNTING',
  SETTINGS_DATA_SECURITY = 'SETTINGS_DATA_SECURITY',
  SETTINGS_MODULES = 'SETTINGS_MODULES',
  ASSETS = 'ASSETS',
  LOCATIONS = 'LOCATIONS'
}

type AppRouteMap<T> = {
  [index in RouteNames]: T;
};

export const Routes: AppRouteMap<string> = {
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
  DEFI_DEPOSITS_LIQUIDITY: '/defi/deposits/liquidity',
  DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2: '/defi/deposits/liquidity/uniswap_v2',
  DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3: '/defi/deposits/liquidity/uniswap_v3',
  DEFI_DEPOSITS_LIQUIDITY_BALANCER: '/defi/deposits/liquidity/balancer',
  DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP: '/defi/deposits/liquidity/sushiswap',
  DEFI_AIRDROPS: '/defi/airdrops',
  STATISTICS: '/statistics',
  STAKING: '/staking/:location*',
  PROFIT_LOSS_REPORTS: '/reports/',
  PROFIT_LOSS_REPORT: `/reports/:id`,
  ASSET_MANAGER: '/asset-manager',
  ASSET_MANAGER_MANAGED: '/asset-manager/managed',
  ASSET_MANAGER_CUSTOM: '/asset-manager/custom',
  ASSET_MANAGER_NEWLY_DETECTED: '/asset-manager/newly-added',
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
  LOCATIONS: '/locations/:identifier'
};

export const useAppRoutes = createSharedComposable(() => {
  const { t } = useI18n();
  const appRoutes = computed(() => ({
    DASHBOARD: {
      route: Routes.DASHBOARD,
      icon: 'dashboard-line',
      text: t('navigation_menu.dashboard')
    },
    ACCOUNTS_BALANCES: {
      route: Routes.ACCOUNTS_BALANCES,
      icon: 'wallet-3-line',
      text: t('navigation_menu.accounts_balances')
    },
    ACCOUNTS_BALANCES_BLOCKCHAIN: {
      route: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
      icon: 'coins-line',
      text: t('navigation_menu.accounts_balances_sub.blockchain_balances')
    },
    ACCOUNTS_BALANCES_EXCHANGE: {
      route: Routes.ACCOUNTS_BALANCES_EXCHANGE,
      icon: 'exchange-line',
      text: t('navigation_menu.accounts_balances_sub.exchange_balances')
    },
    ACCOUNTS_BALANCES_MANUAL: {
      route: Routes.ACCOUNTS_BALANCES_MANUAL,
      icon: 'scales-line',
      text: t('navigation_menu.accounts_balances_sub.manual_balances')
    },
    ACCOUNTS_BALANCES_NON_FUNGIBLE: {
      route: Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE,
      icon: 'scales-fill',
      text: t('navigation_menu.accounts_balances_sub.non_fungible_balances')
    },
    NFTS: {
      route: Routes.NFTS,
      icon: 'image-line',
      text: t('navigation_menu.nfts')
    },
    HISTORY: {
      route: Routes.HISTORY,
      icon: 'history-line',
      text: t('navigation_menu.history')
    },
    HISTORY_TRADES: {
      route: Routes.HISTORY_TRADES,
      icon: 'shuffle-line',
      text: t('navigation_menu.history_sub.trades')
    },
    HISTORY_DEPOSITS_WITHDRAWALS: {
      route: '/history/deposits-withdrawals',
      icon: 'bank-line',
      text: t('navigation_menu.history_sub.deposits_withdrawals')
    },
    HISTORY_EVENTS: {
      route: Routes.HISTORY_EVENTS,
      icon: 'exchange-box-line',
      text: t('navigation_menu.history_sub.history_events')
    },
    DEFI: {
      route: Routes.DEFI,
      icon: 'line-chart-line',
      text: t('navigation_menu.defi')
    },
    DEFI_OVERVIEW: {
      route: Routes.DEFI_OVERVIEW,
      icon: 'bar-chart-box-line',
      text: t('navigation_menu.defi_sub.overview')
    },
    DEFI_DEPOSITS: {
      route: '/defi/deposits',
      icon: 'login-circle-line',
      text: t('common.deposits')
    },
    DEFI_LIABILITIES: {
      route: '/defi/liabilities',
      icon: 'logout-circle-r-line',
      text: t('navigation_menu.defi_sub.liabilities')
    },
    DEFI_DEPOSITS_PROTOCOLS: {
      route: '/defi/deposits/protocols',
      icon: 'login-circle-line',
      text: t('navigation_menu.defi_sub.deposits_sub.protocols')
    },
    DEFI_DEPOSITS_LIQUIDITY: {
      route: '/defi/deposits/liquidity',
      icon: 'login-circle-line',
      text: t('navigation_menu.defi_sub.deposits_sub.liquidity')
    },
    DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2: {
      route: '/defi/deposits/liquidity/uniswap_v2',
      image: './assets/images/protocols/uniswap.svg',
      text: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v2')
    },
    DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3: {
      route: '/defi/deposits/liquidity/uniswap_v3',
      image: './assets/images/protocols/uniswap.svg',
      text: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v3')
    },
    DEFI_DEPOSITS_LIQUIDITY_BALANCER: {
      route: '/defi/deposits/liquidity/balancer',
      image: './assets/images/protocols/balancer.svg',
      text: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.balancer')
    },
    DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP: {
      route: '/defi/deposits/liquidity/sushiswap',
      image: './assets/images/protocols/sushiswap.svg',
      text: t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.sushiswap')
    },
    DEFI_AIRDROPS: {
      route: Routes.DEFI_AIRDROPS,
      icon: 'gift-line',
      text: t('navigation_menu.defi_sub.airdrops')
    },
    STATISTICS: {
      route: Routes.STATISTICS,
      icon: 'file-chart-line',
      text: t('navigation_menu.statistics')
    },
    STAKING: {
      route: Routes.STAKING,
      icon: 'inbox-archive-line',
      text: t('navigation_menu.staking')
    },
    PROFIT_LOSS_REPORTS: {
      route: Routes.PROFIT_LOSS_REPORTS,
      icon: 'calculator-line',
      text: t('navigation_menu.profit_loss_report')
    },
    PROFIT_LOSS_REPORT: {
      route: Routes.PROFIT_LOSS_REPORT,
      icon: 'calculator-line',
      text: t('navigation_menu.profit_loss_report')
    },
    ASSET_MANAGER: {
      route: Routes.ASSET_MANAGER,
      icon: 'database-2-line',
      text: t('navigation_menu.manage_assets')
    },
    ASSET_MANAGER_MANAGED: {
      route: Routes.ASSET_MANAGER_MANAGED,
      icon: 'server-line',
      text: t('navigation_menu.manage_assets_sub.managed_assets')
    },
    ASSET_MANAGER_CUSTOM: {
      route: Routes.ASSET_MANAGER_CUSTOM,
      icon: 'database-line',
      text: t('navigation_menu.manage_assets_sub.custom_assets')
    },
    ASSET_MANAGER_NEWLY_DETECTED: {
      route: Routes.ASSET_MANAGER_NEWLY_DETECTED,
      icon: 'list-radio',
      text: t('navigation_menu.manage_assets_sub.newly_detected')
    },
    PRICE_MANAGER: {
      route: Routes.PRICE_MANAGER,
      icon: 'file-chart-line',
      text: t('navigation_menu.manage_prices')
    },
    PRICE_MANAGER_LATEST: {
      route: Routes.PRICE_MANAGER_LATEST,
      icon: 'calendar-event-line',
      text: t('navigation_menu.manage_prices_sub.latest_prices')
    },
    PRICE_MANAGER_HISTORIC: {
      route: Routes.PRICE_MANAGER_HISTORIC,
      icon: 'calendar-2-line',
      text: t('navigation_menu.manage_prices_sub.historic_prices')
    },
    ADDRESS_BOOK_MANAGER: {
      route: Routes.ADDRESS_BOOK_MANAGER,
      icon: 'book-2-line',
      text: t('navigation_menu.manage_address_book')
    },
    API_KEYS: {
      route: Routes.API_KEYS,
      icon: 'key-line',
      text: t('navigation_menu.api_keys')
    },
    API_KEYS_ROTKI_PREMIUM: {
      route: Routes.API_KEYS_ROTKI_PREMIUM,
      icon: 'vip-crown-line',
      text: t('navigation_menu.api_keys_sub.premium')
    },
    API_KEYS_EXCHANGES: {
      route: Routes.API_KEYS_EXCHANGES,
      icon: 'swap-line',
      text: t('navigation_menu.api_keys_sub.exchanges')
    },
    API_KEYS_EXTERNAL_SERVICES: {
      route: Routes.API_KEYS_EXTERNAL_SERVICES,
      icon: 'links-line',
      text: t('navigation_menu.api_keys_sub.external_services')
    },
    IMPORT: {
      route: Routes.IMPORT,
      icon: 'folder-received-line',
      text: t('navigation_menu.import_data')
    },
    SETTINGS: {
      route: Routes.SETTINGS,
      icon: 'settings-4-fill',
      text: t('navigation_menu.settings')
    },
    SETTINGS_GENERAL: {
      route: Routes.SETTINGS_GENERAL,
      icon: 'settings-4-fill',
      text: t('navigation_menu.settings_sub.general')
    },
    SETTINGS_ACCOUNTING: {
      route: Routes.SETTINGS_ACCOUNTING,
      icon: 'settings-4-fill',
      text: t('navigation_menu.settings_sub.accounting')
    },
    SETTINGS_DATA_SECURITY: {
      route: Routes.SETTINGS_DATA_SECURITY,
      icon: 'settings-4-fill',
      text: t('navigation_menu.settings_sub.data_security')
    },
    SETTINGS_MODULES: {
      route: Routes.SETTINGS_MODULES,
      icon: 'settings-4-fill',
      text: t('navigation_menu.settings_sub.modules')
    },
    ASSETS: {
      route: Routes.ASSETS,
      text: t('common.assets')
    },
    LOCATIONS: {
      route: Routes.LOCATIONS,
      text: t('navigation_menu.locations')
    }
  }));

  return {
    appRoutes
  };
});
