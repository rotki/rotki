import i18n from '@/i18n';

export const routesRef = computed(() => ({
  ROOT: {
    route: '/'
  },
  DASHBOARD: {
    route: '/dashboard',
    icon: 'mdi-monitor-dashboard',
    text: i18n.t('navigation_menu.dashboard').toString()
  },
  ACCOUNTS_BALANCES: {
    route: '/accounts-balances',
    icon: 'mdi-wallet',
    text: i18n.t('navigation_menu.accounts_balances').toString()
  },
  ACCOUNTS_BALANCES_BLOCKCHAIN: {
    route: '/accounts-balances/blockchain-balances',
    icon: 'mdi-wallet',
    text: i18n
      .t('navigation_menu.accounts_balances_sub.blockchain_balances')
      .toString()
  },
  ACCOUNTS_BALANCES_EXCHANGE: {
    route: '/accounts-balances/exchange-balances',
    icon: 'mdi-wallet',
    text: i18n
      .t('navigation_menu.accounts_balances_sub.exchange_balances')
      .toString()
  },
  ACCOUNTS_BALANCES_MANUAL: {
    route: '/accounts-balances/manual-balances',
    icon: 'mdi-wallet',
    text: i18n
      .t('navigation_menu.accounts_balances_sub.manual_balances')
      .toString()
  },
  ACCOUNTS_BALANCES_NON_FUNGIBLE: {
    route: '/accounts-balances/nonfungible',
    icon: 'mdi-wallet',
    text: i18n
      .t('navigation_menu.accounts_balances_sub.non_fungible_balances')
      .toString()
  },
  NFTS: {
    route: '/nfts',
    icon: 'mdi-image-area',
    text: i18n.t('navigation_menu.nfts').toString()
  },
  HISTORY: {
    route: '/history',
    icon: 'mdi-history',
    text: i18n.t('navigation_menu.history').toString()
  },
  HISTORY_TRADES: {
    route: '/history/trades',
    icon: 'mdi-shuffle-variant',
    text: i18n.t('navigation_menu.history_sub.trades').toString()
  },
  HISTORY_DEPOSITS_WITHDRAWALS: {
    route: '/history/deposits-withdrawals',
    icon: 'mdi-bank-transfer',
    text: i18n.t('navigation_menu.history_sub.deposits_withdrawals').toString()
  },
  HISTORY_TRANSACTIONS: {
    route: '/history/transactions',
    icon: 'mdi-swap-horizontal-bold',
    text: i18n.t('navigation_menu.history_sub.ethereum_transactions').toString()
  },
  HISTORY_LEDGER_ACTIONS: {
    route: '/history/ledger-actions',
    icon: 'mdi-book-open-variant',
    text: i18n.t('navigation_menu.history_sub.ledger_actions').toString()
  },
  DEFI: {
    route: '/defi',
    icon: 'mdi-finance',
    text: i18n.t('navigation_menu.defi').toString()
  },
  DEFI_OVERVIEW: {
    route: '/defi/overview',
    icon: 'mdi-chart-box',
    text: i18n.t('navigation_menu.defi_sub.overview').toString()
  },
  DEFI_DEPOSITS: {
    route: '/defi/deposits',
    icon: 'mdi-bank-transfer-in',
    text: i18n.t('common.deposits').toString()
  },
  DEFI_LIABILITIES: {
    route: '/defi/liabilities',
    icon: 'mdi-bank-transfer-out',
    text: i18n.t('navigation_menu.defi_sub.liabilities').toString()
  },
  DEFI_DEPOSITS_PROTOCOLS: {
    route: '/defi/deposits/protocols',
    icon: 'mdi-bank-transfer-out',
    text: i18n.t('navigation_menu.defi_sub.deposits_sub.protocols').toString()
  },
  DEFI_DEPOSITS_LIQUIDITY: {
    route: '/defi/deposits/liquidity',
    icon: 'mdi-bank-transfer-out',
    text: i18n.t('navigation_menu.defi_sub.deposits_sub.liquidity').toString()
  },
  DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V2: {
    route: '/defi/deposits/liquidity/uniswap_v2',
    image: '/assets/images/defi/uniswap.svg',
    text: i18n
      .t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v2')
      .toString()
  },
  DEFI_DEPOSITS_LIQUIDITY_UNISWAP_V3: {
    route: '/defi/deposits/liquidity/uniswap_v3',
    image: '/assets/images/defi/uniswap.svg',
    text: i18n
      .t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.uniswap_v3')
      .toString()
  },
  DEFI_DEPOSITS_LIQUIDITY_BALANCER: {
    route: '/defi/deposits/liquidity/balancer',
    image: '/assets/images/defi/balancer.svg',
    text: i18n
      .t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.balancer')
      .toString()
  },
  DEFI_DEPOSITS_LIQUIDITY_SUSHISWAP: {
    route: '/defi/deposits/liquidity/sushiswap',
    image: '/assets/images/modules/sushiswap.svg',
    text: i18n
      .t('navigation_menu.defi_sub.deposits_sub.liquidity_sub.sushiswap')
      .toString()
  },
  DEFI_AIRDROPS: {
    route: '/defi/airdrops',
    icon: 'mdi-parachute',
    text: i18n.t('navigation_menu.defi_sub.airdrops').toString()
  },
  STATISTICS: {
    route: '/statistics',
    icon: 'mdi-chart-bar',
    text: i18n.t('navigation_menu.statistics').toString()
  },
  STAKING: {
    route: '/staking/:location*',
    icon: 'mdi-inbox-arrow-down',
    text: i18n.t('navigation_menu.staking').toString()
  },
  PROFIT_LOSS_REPORTS: {
    route: '/reports/',
    icon: 'mdi-calculator',
    text: i18n.t('navigation_menu.profit_loss_report').toString()
  },
  PROFIT_LOSS_REPORT: {
    route: `/report/:id`,
    icon: 'mdi-calculator',
    text: i18n.t('navigation_menu.profit_loss_report').toString()
  },
  ASSET_MANAGER: {
    route: '/asset-manager',
    icon: 'mdi-database-edit',
    text: i18n.t('navigation_menu.manage_assets').toString()
  },
  ASSET_MANAGER_MANAGED: {
    route: '/asset-manager/managed',
    icon: 'mdi-database-edit',
    text: i18n.t('navigation_menu.manage_assets_sub.managed_assets').toString()
  },
  ASSET_MANAGER_CUSTOM: {
    route: '/asset-manager/custom',
    icon: 'mdi-database-edit',
    text: i18n.t('navigation_menu.manage_assets_sub.custom_assets').toString()
  },
  PRICE_MANAGER: {
    route: '/price-manager',
    icon: 'mdi-chart-line',
    text: i18n.t('navigation_menu.manage_prices').toString()
  },
  PRICE_MANAGER_LATEST: {
    route: '/price-manager/latest',
    icon: 'mdi-chart-line',
    text: i18n.t('navigation_menu.manage_prices_sub.latest_prices').toString()
  },
  PRICE_MANAGER_HISTORIC: {
    route: '/price-manager/historic',
    icon: 'mdi-chart-line',
    text: i18n.t('navigation_menu.manage_prices_sub.historic_prices').toString()
  },
  ETH_ADDRESS_BOOK_MANAGER: {
    route: '/eth-address-book-manager',
    icon: 'mdi-book-open',
    text: i18n.t('navigation_menu.manage_eth_address_book').toString()
  },
  API_KEYS: {
    route: '/settings/api-keys',
    icon: 'mdi-key-chain-variant',
    text: i18n.t('navigation_menu.api_keys').toString()
  },
  API_KEYS_ROTKI_PREMIUM: {
    route: '/settings/api-keys/rotki-premium',
    icon: 'mdi-key-chain-variant',
    text: i18n.t('navigation_menu.api_keys_sub.premium').toString()
  },
  API_KEYS_EXCHANGES: {
    route: '/settings/api-keys/exchanges',
    icon: 'mdi-key-chain-variant',
    text: i18n.t('navigation_menu.api_keys_sub.exchanges').toString()
  },
  API_KEYS_EXTERNAL_SERVICES: {
    route: '/settings/api-keys/external-services',
    icon: 'mdi-key-chain-variant',
    text: i18n.t('navigation_menu.api_keys_sub.external_services').toString()
  },
  IMPORT: {
    route: '/import',
    icon: 'mdi-database-import',
    text: i18n.t('navigation_menu.import_data').toString()
  },
  SETTINGS: {
    route: '/settings',
    icon: 'mdi-cog',
    text: i18n.t('navigation_menu.settings').toString()
  },
  SETTINGS_GENERAL: {
    route: '/settings/general',
    icon: 'mdi-cog',
    text: i18n.t('navigation_menu.settings_sub.general').toString()
  },
  SETTINGS_ACCOUNTING: {
    route: '/settings/accounting',
    icon: 'mdi-cog',
    text: i18n.t('navigation_menu.settings_sub.accounting').toString()
  },
  SETTINGS_DATA_SECURITY: {
    route: '/settings/data-security',
    icon: 'mdi-cog',
    text: i18n.t('navigation_menu.settings_sub.data_security').toString()
  },
  SETTINGS_MODULES: {
    route: '/settings/modules',
    icon: 'mdi-cog',
    text: i18n.t('navigation_menu.settings_sub.modules').toString()
  },
  ASSETS: {
    route: '/assets/:identifier',
    text: i18n.t('common.assets').toString()
  },
  LOCATIONS: {
    route: '/locations/:identifier',
    text: i18n.t('navigation_menu.locations').toString()
  }
}));

export const Routes = get(routesRef);
