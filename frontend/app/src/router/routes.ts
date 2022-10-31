enum RouteNames {
  ROOT = 'ROOT',
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
  HISTORY_TRANSACTIONS = 'HISTORY_TRANSACTIONS',
  HISTORY_LEDGER_ACTIONS = 'HISTORY_LEDGER_ACTIONS',
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
  PRICE_MANAGER = 'PRICE_MANAGER',
  PRICE_MANAGER_LATEST = 'PRICE_MANAGER_LATEST',
  PRICE_MANAGER_HISTORIC = 'PRICE_MANAGER_HISTORIC',
  ETH_ADDRESS_BOOK_MANAGER = 'ETH_ADDRESS_BOOK_MANAGER',
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
  ACCOUNTS_BALANCES: '/accounts-balances',
  ACCOUNTS_BALANCES_BLOCKCHAIN: '/accounts-balances/blockchain-balances',
  ACCOUNTS_BALANCES_EXCHANGE: '/accounts-balances/exchange-balances',
  ACCOUNTS_BALANCES_MANUAL: '/accounts-balances/manual-balances',
  ACCOUNTS_BALANCES_NON_FUNGIBLE: '/accounts-balances/nonfungible',
  NFTS: '/nfts',
  HISTORY: '/history',
  HISTORY_TRADES: '/history/trades',
  HISTORY_DEPOSITS_WITHDRAWALS: '/history/deposits-withdrawals',
  HISTORY_TRANSACTIONS: '/history/transactions',
  HISTORY_LEDGER_ACTIONS: '/history/ledger-actions',
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
  PROFIT_LOSS_REPORT: `/report/:id`,
  ASSET_MANAGER: '/asset-manager',
  ASSET_MANAGER_MANAGED: '/asset-manager/managed',
  ASSET_MANAGER_CUSTOM: '/asset-manager/custom',
  PRICE_MANAGER: '/price-manager',
  PRICE_MANAGER_LATEST: '/price-manager/latest',
  PRICE_MANAGER_HISTORIC: '/price-manager/historic',
  ETH_ADDRESS_BOOK_MANAGER: '/eth-address-book-manager',
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
  const { tc } = useI18n();
  const appRoutes = computed(() => ({
    ROOT: {
      route: Routes.ROOT
    },
    DASHBOARD: {
      route: Routes.DASHBOARD,
      icon: 'mdi-monitor-dashboard',
      text: tc('navigation_menu.dashboard')
    },
    ACCOUNTS_BALANCES: {
      route: Routes.ACCOUNTS_BALANCES,
      icon: 'mdi-wallet',
      text: tc('navigation_menu.accounts_balances')
    },
    ACCOUNTS_BALANCES_BLOCKCHAIN: {
      route: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN,
      icon: 'mdi-wallet',
      text: tc('navigation_menu.accounts_balances_sub.blockchain_balances')
    },
    ACCOUNTS_BALANCES_EXCHANGE: {
      route: Routes.ACCOUNTS_BALANCES_EXCHANGE,
      icon: 'mdi-wallet',
      text: tc('navigation_menu.accounts_balances_sub.exchange_balances')
    },
    ACCOUNTS_BALANCES_MANUAL: {
      route: Routes.ACCOUNTS_BALANCES_MANUAL,
      icon: 'mdi-wallet',
      text: tc('navigation_menu.accounts_balances_sub.manual_balances')
    },
    ACCOUNTS_BALANCES_NON_FUNGIBLE: {
      route: Routes.ACCOUNTS_BALANCES_NON_FUNGIBLE,
      icon: 'mdi-wallet',
      text: tc('navigation_menu.accounts_balances_sub.non_fungible_balances')
    },
    NFTS: {
      route: Routes.NFTS,
      icon: 'mdi-image-area',
      text: tc('navigation_menu.nfts')
    },
    HISTORY: {
      route: Routes.HISTORY,
      icon: 'mdi-history',
      text: tc('navigation_menu.history')
    },
    HISTORY_TRADES: {
      route: Routes.HISTORY_TRADES,
      icon: 'mdi-shuffle-variant',
      text: tc('navigation_menu.history_sub.trades')
    },
    HISTORY_DEPOSITS_WITHDRAWALS: {
      route: '/history/deposits-withdrawals',
      icon: 'mdi-bank-transfer',
      text: tc('navigation_menu.history_sub.deposits_withdrawals')
    },
    HISTORY_TRANSACTIONS: {
      route: Routes.HISTORY_TRANSACTIONS,
      icon: 'mdi-swap-horizontal-bold',
      text: tc('navigation_menu.history_sub.ethereum_transactions')
    },
    HISTORY_LEDGER_ACTIONS: {
      route: Routes.HISTORY_LEDGER_ACTIONS,
      icon: 'mdi-book-open-variant',
      text: tc('navigation_menu.history_sub.ledger_actions')
    },
    DEFI: {
      route: Routes.DEFI,
      icon: 'mdi-finance',
      text: tc('navigation_menu.defi')
    },
    DEFI_OVERVIEW: {
      route: Routes.DEFI_OVERVIEW,
      icon: 'mdi-chart-box',
      text: tc('navigation_menu.defi_sub.overview')
    },
    DEFI_DEPOSITS: {
      route: '/defi/deposits',
      icon: 'mdi-bank-transfer-in',
      text: tc('common.deposits')
    },
    DEFI_LIABILITIES: {
      route: '/defi/liabilities',
      icon: 'mdi-bank-transfer-out',
      text: tc('navigation_menu.defi_sub.liabilities')
    },
    DEFI_DEPOSITS_PROTOCOLS: {
      route: '/defi/deposits/protocols',
      icon: 'mdi-bank-transfer-out',
      text: tc('navigation_menu.defi_sub.deposits_sub.protocols')
    },
    DEFI_DEPOSITS_LIQUIDITY: {
      route: '/defi/deposits/liquidity',
      icon: 'mdi-bank-transfer-out',
      text: tc('navigation_menu.defi_sub.deposits_sub.liquidity')
    },
    DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2: {
      route: '/defi/deposits/liquidity/uniswap_v2',
      image: '/assets/images/defi/uniswap.svg',
      text: tc('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v2')
    },
    DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3: {
      route: '/defi/deposits/liquidity/uniswap_v3',
      image: '/assets/images/defi/uniswap.svg',
      text: tc('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v3')
    },
    DEFI_DEPOSITS_LIQUIDITY_BALANCER: {
      route: '/defi/deposits/liquidity/balancer',
      image: '/assets/images/defi/balancer.svg',
      text: tc('navigation_menu.defi_sub.deposits_sub.liquidity_sub.balancer')
    },
    DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP: {
      route: '/defi/deposits/liquidity/sushiswap',
      image: '/assets/images/modules/sushiswap.svg',
      text: tc('navigation_menu.defi_sub.deposits_sub.liquidity_sub.sushiswap')
    },
    DEFI_AIRDROPS: {
      route: Routes.DEFI_AIRDROPS,
      icon: 'mdi-parachute',
      text: tc('navigation_menu.defi_sub.airdrops')
    },
    STATISTICS: {
      route: Routes.STATISTICS,
      icon: 'mdi-chart-bar',
      text: tc('navigation_menu.statistics')
    },
    STAKING: {
      route: Routes.STAKING,
      icon: 'mdi-inbox-arrow-down',
      text: tc('navigation_menu.staking')
    },
    PROFIT_LOSS_REPORTS: {
      route: Routes.PROFIT_LOSS_REPORTS,
      icon: 'mdi-calculator',
      text: tc('navigation_menu.profit_loss_report')
    },
    PROFIT_LOSS_REPORT: {
      route: Routes.PROFIT_LOSS_REPORT,
      icon: 'mdi-calculator',
      text: tc('navigation_menu.profit_loss_report')
    },
    ASSET_MANAGER: {
      route: Routes.ASSET_MANAGER,
      icon: 'mdi-database-edit',
      text: tc('navigation_menu.manage_assets')
    },
    ASSET_MANAGER_MANAGED: {
      route: Routes.ASSET_MANAGER_MANAGED,
      icon: 'mdi-database-edit',
      text: tc('navigation_menu.manage_assets_sub.managed_assets')
    },
    ASSET_MANAGER_CUSTOM: {
      route: Routes.ASSET_MANAGER_CUSTOM,
      icon: 'mdi-database-edit',
      text: tc('navigation_menu.manage_assets_sub.custom_assets')
    },
    PRICE_MANAGER: {
      route: Routes.PRICE_MANAGER,
      icon: 'mdi-chart-line',
      text: tc('navigation_menu.manage_prices')
    },
    PRICE_MANAGER_LATEST: {
      route: Routes.PRICE_MANAGER_LATEST,
      icon: 'mdi-chart-line',
      text: tc('navigation_menu.manage_prices_sub.latest_prices')
    },
    PRICE_MANAGER_HISTORIC: {
      route: Routes.PRICE_MANAGER_HISTORIC,
      icon: 'mdi-chart-line',
      text: tc('navigation_menu.manage_prices_sub.historic_prices')
    },
    ETH_ADDRESS_BOOK_MANAGER: {
      route: Routes.ETH_ADDRESS_BOOK_MANAGER,
      icon: 'mdi-book-open',
      text: tc('navigation_menu.manage_eth_address_book')
    },
    API_KEYS: {
      route: Routes.API_KEYS,
      icon: 'mdi-key-chain-variant',
      text: tc('navigation_menu.api_keys')
    },
    API_KEYS_ROTKI_PREMIUM: {
      route: Routes.API_KEYS_ROTKI_PREMIUM,
      icon: 'mdi-key-chain-variant',
      text: tc('navigation_menu.api_keys_sub.premium')
    },
    API_KEYS_EXCHANGES: {
      route: Routes.API_KEYS_EXCHANGES,
      icon: 'mdi-key-chain-variant',
      text: tc('navigation_menu.api_keys_sub.exchanges')
    },
    API_KEYS_EXTERNAL_SERVICES: {
      route: Routes.API_KEYS_EXTERNAL_SERVICES,
      icon: 'mdi-key-chain-variant',
      text: tc('navigation_menu.api_keys_sub.external_services')
    },
    IMPORT: {
      route: Routes.IMPORT,
      icon: 'mdi-database-import',
      text: tc('navigation_menu.import_data')
    },
    SETTINGS: {
      route: Routes.SETTINGS,
      icon: 'mdi-cog',
      text: tc('navigation_menu.settings')
    },
    SETTINGS_GENERAL: {
      route: Routes.SETTINGS_GENERAL,
      icon: 'mdi-cog',
      text: tc('navigation_menu.settings_sub.general')
    },
    SETTINGS_ACCOUNTING: {
      route: Routes.SETTINGS_ACCOUNTING,
      icon: 'mdi-cog',
      text: tc('navigation_menu.settings_sub.accounting')
    },
    SETTINGS_DATA_SECURITY: {
      route: Routes.SETTINGS_DATA_SECURITY,
      icon: 'mdi-cog',
      text: tc('navigation_menu.settings_sub.data_security')
    },
    SETTINGS_MODULES: {
      route: Routes.SETTINGS_MODULES,
      icon: 'mdi-cog',
      text: tc('navigation_menu.settings_sub.modules')
    },
    ASSETS: {
      route: Routes.ASSETS,
      text: tc('common.assets')
    },
    LOCATIONS: {
      route: Routes.LOCATIONS,
      text: tc('navigation_menu.locations')
    }
  }));

  return {
    appRoutes
  };
});
