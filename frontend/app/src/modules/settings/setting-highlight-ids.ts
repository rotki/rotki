import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';

export const SettingsHighlightIds = {
  ABBREVIATION: 'setting-abbreviation',
  ACCOUNTING_RULE: 'setting-accounting-rule',
  ACCOUNTING_TRADE: 'setting-accounting-trade',
  AMOUNT_FORMAT: 'setting-amount-format',
  ANIMATIONS: 'setting-animations',
  ASK_SIZE_DISCREPANCY: 'setting-ask-size-discrepancy',
  ASSET_UPDATE: 'setting-asset-update',
  AUTO_CREATE_PROFIT_EVENTS: 'setting-auto-create-profit-events',
  AUTO_DETECT_TOKENS: 'setting-auto-detect-tokens',
  BALANCE_SAVE_FREQUENCY: 'setting-balance-save-frequency',
  BTC_DERIVATION_GAP: 'setting-btc-derivation-gap',
  CHAINS_TO_SKIP_DETECTION: 'setting-chains-to-skip-detection',
  CHANGE_PASSWORD: 'setting-change-password',
  CONNECT_TIMEOUT: 'setting-connect-timeout',
  CSV_EXPORT: 'setting-csv-export',
  CURRENCY_LOCATION: 'setting-currency-location',
  DATE_FORMAT: 'setting-date-format',
  DISMISSAL_THRESHOLD: 'setting-dismissal-threshold',
  DISPLAY_DATE_IN_LOCALTIME: 'setting-display-date-in-localtime',
  EXPLORERS: 'setting-explorers',
  GLOBALDB_INFO: 'setting-globaldb-info',
  GOLDRUSH_API_KEY: 'setting-goldrush-api-key',
  GRAPH_BASIS: 'setting-graph-basis',
  INTERNAL_TX_CONFLICT_REPULL: 'setting-internal-tx-conflict-repull',
  LANGUAGE: 'setting-language',
  LOG_LEVEL: 'setting-log-level',
  MIN_OUT_OF_SYNC_PERIOD: 'setting-min-out-of-sync-period',
  MODULES: 'setting-modules',
  NEWLY_DETECTED_TOKENS_MAX_COUNT: 'setting-newly-detected-tokens-max-count',
  NEWLY_DETECTED_TOKENS_TTL: 'setting-newly-detected-tokens-ttl',
  NFT_IMAGE_RENDERING: 'setting-nft-image-rendering',
  NFT_IN_NET_VALUE: 'setting-nft-in-net-value',
  ORACLE_PENALTY_DURATION: 'setting-oracle-penalty-duration',
  ORACLE_PENALTY_THRESHOLD: 'setting-oracle-penalty-threshold',
  PASSWORD_CONFIRMATION: 'setting-password-confirmation',
  PERIODIC_QUERY: 'setting-periodic-query',
  PERSIST_PRIVACY: 'setting-persist-privacy',
  PERSIST_TABLE_SORTING: 'setting-persist-table-sorting',
  PURGE_DATA: 'setting-purge-data',
  PURGE_IMAGES_CACHE: 'setting-purge-images-cache',
  QUERY_RETRY_LIMIT: 'setting-query-retry-limit',
  READ_TIMEOUT: 'setting-read-timeout',
  REFRESH_BALANCE: 'setting-refresh-balance',
  REFRESH_CACHE: 'setting-refresh-cache',
  RESET_DISMISSAL_STATUS: 'setting-reset-dismissal-status',
  RESTORE_ASSETS_DB: 'setting-restore-assets-db',
  ROUNDING: 'setting-rounding',
  RPC_NODES: 'setting-rpc-nodes',
  SCRAMBLE: 'setting-scramble',
  SKIPPED_EVENTS: 'setting-skipped-events',
  SUBSCRIPT: 'setting-subscript',
  SUPPRESS_MISSING_KEY: 'setting-suppress-missing-key',
  TIMEFRAME: 'setting-timeframe',
  TREAT_ETH2_AS_ETH: 'setting-treat-eth2-as-eth',
  USAGE_ANALYTICS: 'setting-usage-analytics',
  USERDB_INFO: 'setting-userdb-info',
  VERSION_UPDATE_CHECK: 'setting-version-update-check',
} as const;

export type SettingsHighlightId = typeof SettingsHighlightIds[keyof typeof SettingsHighlightIds];

export const SettingsCategoryIds = {
  ALIAS: 'alias',
  AMOUNT: 'amount',
  ASSET_DATABASE: 'asset_database',
  BACKEND: 'backend',
  CACHE_MANAGEMENT: 'cache_management',
  CHAINS: 'chains',
  DATABASE_INFO: 'database_info',
  EXTERNAL_SERVICE: 'external_service',
  GENERAL: 'general',
  GRAPH: 'graph',
  HISTORY_EVENT: 'history_event',
  IMPORT_EXPORT: 'import_export',
  INDEXER: 'indexer',
  INTERFACE_ONLY: 'interface_only',
  MANAGE_DATA: 'manage_data',
  NEWLY_DETECTED_TOKENS: 'newly_detected_tokens',
  NFT: 'nft',
  PENALTY: 'penalty',
  PRICE_ORACLE: 'price_oracle',
  SECURITY: 'security',
  THEME: 'theme',
  USER_BACKUPS: 'user_backups',
} as const;

export type SettingsCategoryId = typeof SettingsCategoryIds[keyof typeof SettingsCategoryIds];

export interface SettingsSearchEntry {
  texts: string[];
  route: RouteLocationRaw;
  icon: RuiIcons;
  categoryId?: SettingsCategoryId;
  highlightId?: SettingsHighlightId;
  keywords?: string[];
}
