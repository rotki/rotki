import { msg } from '@/message-key';
import { SettingsCategoryIds, SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { general, type RegistryEntry } from '@/modules/settings/settings-channels';

/** The `general` channel's registry slice: settings persisted on the backend `GeneralSettings` object. */
export const generalRegistry = {
  activeModules: general('activeModules'),
  addressNamePriority: general('addressNamePriority'),
  askUserUponSizeDiscrepancy: general('askUserUponSizeDiscrepancy', {
    anchor: SettingsHighlightIds.ASK_SIZE_DISCREPANCY,
    search: { category: SettingsCategoryIds.GENERAL, titleKey: msg.$t('sync_indicator.setting.ask_user_upon_size_discrepancy.title') },
  }),
  assetMovementAmountTolerance: general('assetMovementAmountTolerance'),
  assetMovementTimeRange: general('assetMovementTimeRange'),
  bridgeMatchAmountTolerance: general('bridgeMatchAmountTolerance'),
  bridgeMatchTimeRange: general('bridgeMatchTimeRange'),
  autoCreateCalendarReminders: general('autoCreateCalendarReminders'),
  autoCreateProfitEvents: general('autoCreateProfitEvents', {
    anchor: SettingsHighlightIds.AUTO_CREATE_PROFIT_EVENTS,
    search: { category: SettingsCategoryIds.HISTORY_EVENT, titleKey: msg.$t('general_settings.history_event.auto_create_profit_events.title') },
  }),
  autoDeleteCalendarEntries: general('autoDeleteCalendarEntries'),
  autoDetectTokens: general('autoDetectTokens', {
    anchor: SettingsHighlightIds.AUTO_DETECT_TOKENS,
    search: { category: SettingsCategoryIds.GENERAL, titleKey: msg.$t('general_settings.auto_detect_tokens.title') },
  }),
  balanceSaveFrequency: general('balanceSaveFrequency', {
    anchor: SettingsHighlightIds.BALANCE_SAVE_FREQUENCY,
    search: { category: SettingsCategoryIds.GENERAL, titleKey: msg.$t('general_settings.balance_frequency.title') },
  }),
  beaconRpcEndpoint: general('beaconRpcEndpoint'),
  btcDerivationGapLimit: general('btcDerivationGapLimit', {
    anchor: SettingsHighlightIds.BTC_DERIVATION_GAP,
    search: { category: SettingsCategoryIds.GENERAL, titleKey: msg.$t('general_settings.labels.btc_derivation_gap') },
  }),
  btcMempoolApi: general('btcMempoolApi'),
  connectTimeout: general('connectTimeout', {
    anchor: SettingsHighlightIds.CONNECT_TIMEOUT,
    search: {
      category: SettingsCategoryIds.EXTERNAL_SERVICE,
      keywords: [msg.$t('general_settings.external_service_setting.label.connect_timeout_hint')],
      titleKey: msg.$t('general_settings.external_service_setting.label.connect_timeout'),
    },
  }),
  csvExportDelimiter: general('csvExportDelimiter', { anchor: SettingsHighlightIds.CSV_EXPORT }),
  currency: general('mainCurrency', {
    anchor: SettingsHighlightIds.AMOUNT_FORMAT,
    encode: value => value.tickerSymbol,
    search: { category: SettingsCategoryIds.AMOUNT, titleKey: msg.$t('general_settings.amount.label.amount') },
  }),
  currencySymbol: general.projected(settings => settings.mainCurrency.tickerSymbol),
  currentPriceOracles: general('currentPriceOracles'),
  dateDisplayFormat: general('dateDisplayFormat', {
    anchor: SettingsHighlightIds.DATE_FORMAT,
    search: { category: SettingsCategoryIds.GENERAL, titleKey: msg.$t('date_format_help.title') },
  }),
  defaultEvmIndexerOrder: general('defaultEvmIndexerOrder'),
  disabledChainQueries: general('disabledChainQueries', {
    anchor: SettingsHighlightIds.DISABLED_CHAIN_QUERIES,
    search: {
      category: SettingsCategoryIds.CHAIN_QUERIES,
      keywords: [msg.$t('general_settings.disabled_chain_queries.subtitle')],
      titleKey: msg.$t('general_settings.disabled_chain_queries.title'),
    },
  }),
  displayDateInLocaltime: general('displayDateInLocaltime', {
    anchor: SettingsHighlightIds.DISPLAY_DATE_IN_LOCALTIME,
    search: { category: SettingsCategoryIds.GENERAL, titleKey: msg.$t('general_settings.display_date_in_localtime.title') },
  }),
  dotRpcEndpoint: general('dotRpcEndpoint'),
  evmIndexersOrder: general('evmIndexersOrder'),
  evmchainsToSkipDetection: general('evmchainsToSkipDetection', {
    anchor: SettingsHighlightIds.CHAINS_TO_SKIP_DETECTION,
    search: {
      category: SettingsCategoryIds.CHAIN_QUERIES,
      keywords: [
        msg.$t('evm_settings.general.chains_to_skip_detection.subtitle'),
        msg.$t('evm_settings.general.chains_to_skip_detection.search_keywords'),
      ],
      titleKey: msg.$t('evm_settings.general.chains_to_skip_detection.title'),
    },
  }),
  floatingPrecision: general('uiFloatingPrecision', { anchor: SettingsHighlightIds.AMOUNT_FORMAT }),
  historicalPriceOracles: general('historicalPriceOracles'),
  inferZeroTimedBalances: general('inferZeroTimedBalances'),
  internalTxConflictRepullFrequency: general('internalTxConflictRepullFrequency', {
    anchor: SettingsHighlightIds.INTERNAL_TX_CONFLICT_REPULL,
    search: { category: SettingsCategoryIds.HISTORY_EVENT, titleKey: msg.$t('general_settings.history_event.internal_tx_conflicts.title') },
  }),
  internalTxsToRepull: general('internalTxsToRepull', { anchor: SettingsHighlightIds.INTERNAL_TX_CONFLICT_REPULL }),
  ksmRpcEndpoint: general('ksmRpcEndpoint'),
  nonSyncingExchanges: general('nonSyncingExchanges'),
  oraclePenaltyDuration: general('oraclePenaltyDuration', {
    anchor: SettingsHighlightIds.ORACLE_PENALTY_DURATION,
    search: { category: SettingsCategoryIds.PENALTY, titleKey: msg.$t('oracle_cache_management.penalty.labels.oracle_penalty_duration') },
  }),
  oraclePenaltyThresholdCount: general('oraclePenaltyThresholdCount', {
    anchor: SettingsHighlightIds.ORACLE_PENALTY_THRESHOLD,
    search: { category: SettingsCategoryIds.PENALTY, titleKey: msg.$t('oracle_cache_management.penalty.labels.oracle_penalty_threshold_count') },
  }),
  queryRetryLimit: general('queryRetryLimit', {
    anchor: SettingsHighlightIds.QUERY_RETRY_LIMIT,
    search: {
      category: SettingsCategoryIds.EXTERNAL_SERVICE,
      keywords: [msg.$t('general_settings.external_service_setting.label.query_retry_limit_hint')],
      titleKey: msg.$t('general_settings.external_service_setting.label.query_retry_limit'),
    },
  }),
  readTimeout: general('readTimeout', {
    anchor: SettingsHighlightIds.READ_TIMEOUT,
    search: {
      category: SettingsCategoryIds.EXTERNAL_SERVICE,
      keywords: [msg.$t('general_settings.external_service_setting.label.read_timeout_hint')],
      titleKey: msg.$t('general_settings.external_service_setting.label.read_timeout'),
    },
  }),
  ssfGraphMultiplier: general('ssfGraphMultiplier'),
  submitUsageAnalytics: general('submitUsageAnalytics', {
    anchor: SettingsHighlightIds.USAGE_ANALYTICS,
    search: { category: SettingsCategoryIds.GENERAL, titleKey: msg.$t('general_settings.usage_analytics.title') },
  }),
  suppressMissingKeyMsgServices: general('suppressMissingKeyMsgServices', {
    anchor: SettingsHighlightIds.SUPPRESS_MISSING_KEY,
    search: {
      category: SettingsCategoryIds.EXTERNAL_SERVICE,
      keywords: [msg.$t('general_settings.external_service_setting.suppress_missing_key.subtitle')],
      titleKey: msg.$t('general_settings.external_service_setting.suppress_missing_key.title'),
    },
  }),
  treatEth2AsEth: general('treatEth2AsEth', {
    anchor: SettingsHighlightIds.TREAT_ETH2_AS_ETH,
    search: {
      category: SettingsCategoryIds.CHAINS,
      keywords: [msg.$t('evm_settings.general.treat_eth2_as_eth.subtitle')],
      titleKey: msg.$t('evm_settings.general.treat_eth2_as_eth.title'),
    },
  }),
} satisfies Record<string, RegistryEntry>;
