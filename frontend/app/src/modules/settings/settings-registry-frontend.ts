import type { FrontendSettings } from '@/modules/settings/types/frontend-settings';
import { BigNumber } from '@rotki/common';
import { msg } from '@/message-key';
import { getBnFormat } from '@/modules/assets/amount-display/amount-formatter';
import { PrivacyMode } from '@/modules/session/types';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { SettingsCategoryIds, SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import { frontend, type RegistryEntry } from '@/modules/settings/settings-channels';

/** Post-persist effect: reconfigure BigNumber's global format when the separators change. */
function applyBigNumberFormat(settings: FrontendSettings): void {
  BigNumber.config({ FORMAT: getBnFormat(settings.thousandSeparator, settings.decimalSeparator) });
}

/** The `frontend` channel's registry slice: settings persisted in the frontend settings store. */
export const frontendRegistry = {
  abbreviateNumber: frontend('abbreviateNumber', {
    anchor: SettingsHighlightIds.ABBREVIATION,
    search: { category: SettingsCategoryIds.AMOUNT, titleKey: msg.$t('general_settings.amount.label.abbreviation') },
  }),
  amountRoundingMode: frontend('amountRoundingMode', {
    anchor: SettingsHighlightIds.ROUNDING,
    search: {
      category: SettingsCategoryIds.AMOUNT,
      keywords: [msg.$t('rounding_settings.subtitle')],
      titleKey: msg.$t('rounding_settings.title'),
    },
  }),
  autoDetectTokensCooldownHours: frontend('autoDetectTokensCooldownHours', {
    anchor: SettingsHighlightIds.AUTO_DETECT_TOKENS_COOLDOWN,
    search: {
      category: SettingsCategoryIds.GENERAL,
      keywords: [msg.$t('general_settings.auto_detect_tokens_cooldown.subtitle')],
      titleKey: msg.$t('general_settings.auto_detect_tokens_cooldown.title'),
    },
  }),
  autoDetectTokensOnLogin: frontend('autoDetectTokensOnLogin', {
    anchor: SettingsHighlightIds.AUTO_DETECT_TOKENS_ON_LOGIN,
    search: {
      category: SettingsCategoryIds.GENERAL,
      keywords: [msg.$t('general_settings.auto_detect_tokens_on_login.subtitle')],
      titleKey: msg.$t('general_settings.auto_detect_tokens_on_login.title'),
    },
  }),
  balanceValueThreshold: frontend('balanceValueThreshold'),
  blockchainRefreshButtonBehaviour: frontend('blockchainRefreshButtonBehaviour'),
  currencyLocation: frontend('currencyLocation', {
    anchor: SettingsHighlightIds.CURRENCY_LOCATION,
    search: { category: SettingsCategoryIds.AMOUNT, titleKey: msg.$t('general_settings.amount.label.currency_location') },
  }),
  darkTheme: frontend('darkTheme'),
  dashboardTablesVisibleColumns: frontend('dashboardTablesVisibleColumns', { userFacing: false }),
  dateInputFormat: frontend('dateInputFormat'),
  decimalSeparator: frontend('decimalSeparator', { anchor: SettingsHighlightIds.AMOUNT_FORMAT, effects: [applyBigNumberFormat] }),
  defaultThemeVersion: frontend('defaultThemeVersion'),
  enableAliasNames: frontend('enableAliasNames'),
  enablePasswordConfirmation: frontend('enablePasswordConfirmation', {
    anchor: SettingsHighlightIds.PASSWORD_CONFIRMATION,
    search: {
      category: SettingsCategoryIds.SECURITY,
      keywords: [msg.$t('password_confirmation_setting.subtitle')],
      titleKey: msg.$t('password_confirmation_setting.title'),
    },
  }),
  evmQueryIndicatorDismissalThreshold: frontend('evmQueryIndicatorDismissalThreshold', {
    anchor: SettingsHighlightIds.DISMISSAL_THRESHOLD,
    search: {
      category: SettingsCategoryIds.INTERFACE_ONLY,
      group: msg.$t('frontend_settings.history_query_indicator.title'),
      keywords: [msg.$t('frontend_settings.history_query_indicator.dismissal_threshold.subtitle')],
      titleKey: msg.$t('frontend_settings.history_query_indicator.dismissal_threshold.title'),
    },
  }),
  evmQueryIndicatorMinOutOfSyncPeriod: frontend('evmQueryIndicatorMinOutOfSyncPeriod', {
    anchor: SettingsHighlightIds.MIN_OUT_OF_SYNC_PERIOD,
    search: {
      category: SettingsCategoryIds.INTERFACE_ONLY,
      group: msg.$t('frontend_settings.history_query_indicator.title'),
      keywords: [msg.$t('frontend_settings.history_query_indicator.min_out_of_sync_period.subtitle')],
      titleKey: msg.$t('frontend_settings.history_query_indicator.min_out_of_sync_period.title'),
    },
  }),
  explorers: frontend('explorers', {
    anchor: SettingsHighlightIds.EXPLORERS,
    search: {
      category: SettingsCategoryIds.INTERFACE_ONLY,
      keywords: [msg.$t('explorers.subtitle')],
      titleKey: msg.$t('explorers.title'),
    },
  }),
  gnosisPaySafeMigrationLastNotified: frontend('gnosisPaySafeMigrationLastNotified', { userFacing: false }),
  gnosisPaySafeMigrationNeverNotify: frontend('gnosisPaySafeMigrationNeverNotify'),
  graphZeroBased: frontend('graphZeroBased', {
    anchor: SettingsHighlightIds.GRAPH_BASIS,
    search: { category: SettingsCategoryIds.GRAPH, titleKey: msg.$t('frontend_settings.graph_basis.title') },
  }),
  ignoreSnapshotError: frontend('ignoreSnapshotError'),
  itemsPerPage: frontend('itemsPerPage', { mirror: useItemsPerPage }),
  language: frontend('language', {
    anchor: SettingsHighlightIds.LANGUAGE,
    search: {
      category: SettingsCategoryIds.INTERFACE_ONLY,
      keywords: [msg.$t('general_settings.language.subtitle')],
      titleKey: msg.$t('general_settings.language.title'),
    },
  }),
  lastAppliedSettingsVersion: frontend('lastAppliedSettingsVersion', { userFacing: false }),
  lastAutoDetectAt: frontend('lastAutoDetectAt', { userFacing: false }),
  lastKnownTimeframe: frontend('lastKnownTimeframe', { userFacing: false }),
  lastPasswordConfirmed: frontend('lastPasswordConfirmed', { userFacing: false }),
  lightTheme: frontend('lightTheme'),
  minimumDigitToBeAbbreviated: frontend('minimumDigitToBeAbbreviated', { anchor: SettingsHighlightIds.ABBREVIATION }),
  newlyDetectedTokensMaxCount: frontend('newlyDetectedTokensMaxCount', {
    anchor: SettingsHighlightIds.NEWLY_DETECTED_TOKENS_MAX_COUNT,
    search: { category: SettingsCategoryIds.NEWLY_DETECTED_TOKENS, titleKey: msg.$t('frontend_settings.newly_detected_tokens.max_count.title') },
  }),
  newlyDetectedTokensTtlDays: frontend('newlyDetectedTokensTtlDays', {
    anchor: SettingsHighlightIds.NEWLY_DETECTED_TOKENS_TTL,
    search: { category: SettingsCategoryIds.NEWLY_DETECTED_TOKENS, titleKey: msg.$t('frontend_settings.newly_detected_tokens.ttl_days.title') },
  }),
  nftsInNetValue: frontend('nftsInNetValue', {
    anchor: SettingsHighlightIds.NFT_IN_NET_VALUE,
    search: {
      category: SettingsCategoryIds.NFT,
      keywords: [msg.$t('general_settings.nft_setting.label.include_nfts_hint')],
      titleKey: msg.$t('general_settings.nft_setting.label.include_nfts_subtitle'),
    },
  }),
  // Machine state written by the notification nag schedule, not a setting the user edits, so it
  // gets no anchor and no search row.
  notificationSchedule: frontend('notificationSchedule'),
  notifyNewNfts: frontend('notifyNewNfts', { anchor: SettingsHighlightIds.NFT_IMAGE_RENDERING }),
  passwordConfirmationInterval: frontend('passwordConfirmationInterval', { anchor: SettingsHighlightIds.PASSWORD_CONFIRMATION }),
  persistPrivacySettings: frontend('persistPrivacySettings', {
    anchor: SettingsHighlightIds.PERSIST_PRIVACY,
    search: { category: SettingsCategoryIds.INTERFACE_ONLY, titleKey: msg.$t('frontend_settings.persist_privacy.title') },
  }),
  persistTableSorting: frontend('persistTableSorting', {
    anchor: SettingsHighlightIds.PERSIST_TABLE_SORTING,
    search: {
      category: SettingsCategoryIds.INTERFACE_ONLY,
      keywords: [msg.$t('frontend_settings.persist_table_sorting.subtitle')],
      titleKey: msg.$t('frontend_settings.persist_table_sorting.title'),
    },
  }),
  privacyMode: frontend('privacyMode'),
  profitLossReportPeriod: frontend('profitLossReportPeriod'),
  queryPeriod: frontend('queryPeriod', {
    anchor: SettingsHighlightIds.PERIODIC_QUERY,
    search: { category: SettingsCategoryIds.INTERFACE_ONLY, titleKey: msg.$t('frontend_settings.periodic_query.title') },
  }),
  refreshPeriod: frontend('refreshPeriod', {
    anchor: SettingsHighlightIds.REFRESH_BALANCE,
    search: { category: SettingsCategoryIds.INTERFACE_ONLY, titleKey: msg.$t('frontend_settings.refresh_balance.title') },
  }),
  renderAllNftImages: frontend('renderAllNftImages', {
    anchor: SettingsHighlightIds.NFT_IMAGE_RENDERING,
    search: {
      category: SettingsCategoryIds.NFT,
      keywords: [msg.$t('general_settings.nft_setting.subtitle.nft_images_rendering_setting_hint')],
      titleKey: msg.$t('general_settings.nft_setting.subtitle.nft_images_rendering_setting'),
    },
  }),
  savedFilters: frontend('savedFilters', { userFacing: false }),
  scrambleData: frontend('scrambleData', {
    anchor: SettingsHighlightIds.SCRAMBLE,
    search: { category: SettingsCategoryIds.INTERFACE_ONLY, titleKey: msg.$t('frontend_settings.scramble.title') },
  }),
  scrambleMultiplier: frontend('scrambleMultiplier', { anchor: SettingsHighlightIds.SCRAMBLE }),
  selectedTheme: frontend('selectedTheme'),
  shouldShowAmount: frontend.projected(settings => settings.privacyMode < PrivacyMode.SEMI_PRIVATE),
  shouldShowPercentage: frontend.projected(settings => settings.privacyMode < PrivacyMode.PRIVATE),
  showGraphRangeSelector: frontend('showGraphRangeSelector'),
  silentNotifications: frontend('silentNotifications'),
  subscriptDecimals: frontend('subscriptDecimals', {
    anchor: SettingsHighlightIds.SUBSCRIPT,
    search: {
      category: SettingsCategoryIds.AMOUNT,
      keywords: [msg.$t('rounding_settings.subscript.subtitle')],
      titleKey: msg.$t('rounding_settings.subscript.title'),
    },
  }),
  suppressNoIndexerChains: frontend('suppressNoIndexerChains', {
    anchor: SettingsHighlightIds.SUPPRESSED_NO_INDEXER_CHAINS,
    search: {
      category: SettingsCategoryIds.INDEXER,
      keywords: [msg.$t('evm_settings.indexer.suppressed_no_indexer_chains.subtitle')],
      titleKey: msg.$t('evm_settings.indexer.suppressed_no_indexer_chains.title'),
    },
  }),
  thousandSeparator: frontend('thousandSeparator', { anchor: SettingsHighlightIds.AMOUNT_FORMAT, effects: [applyBigNumberFormat] }),
  timeframeSetting: frontend('timeframeSetting', {
    anchor: SettingsHighlightIds.TIMEFRAME,
    search: {
      category: SettingsCategoryIds.GRAPH,
      keywords: [msg.$t('timeframe_settings.default_timeframe_description')],
      titleKey: msg.$t('timeframe_settings.default_timeframe'),
    },
  }),
  useHistoricalAssetBalances: frontend('useHistoricalAssetBalances'),
  valueRoundingMode: frontend('valueRoundingMode', { anchor: SettingsHighlightIds.ROUNDING }),
  versionUpdateCheckFrequency: frontend('versionUpdateCheckFrequency', {
    anchor: SettingsHighlightIds.VERSION_UPDATE_CHECK,
    search: { category: SettingsCategoryIds.GENERAL, titleKey: msg.$t('general_settings.version_update_check.title') },
  }),
  visibleTimeframes: frontend('visibleTimeframes', { anchor: SettingsHighlightIds.TIMEFRAME }),
  whitelistedDomainsForNftImages: frontend('whitelistedDomainsForNftImages', { anchor: SettingsHighlightIds.NFT_IMAGE_RENDERING }),
} satisfies Record<string, RegistryEntry>;
