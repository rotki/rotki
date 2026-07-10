import type { Ref } from 'vue';
import type { FrontendSettings } from '@/modules/settings/types/frontend-settings';
import type { AccountingSettings, GeneralSettings } from '@/modules/settings/types/user-settings';
import { BigNumber } from '@rotki/common';
import { getBnFormat } from '@/modules/assets/amount-display/amount-formatter';
import { PrivacyMode, type SessionSettings } from '@/modules/session/types';
import { useAnimationsEnabled } from '@/modules/session/use-animations-enabled';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { type SettingsHighlightId, SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';

/** Post-persist effect: reconfigure BigNumber's global format when the separators change. */
function applyBigNumberFormat(settings: FrontendSettings): void {
  BigNumber.config({ FORMAT: getBnFormat(settings.thousandSeparator, settings.decimalSeparator) });
}

/** Channel tag object: the single definition of the four settings channels. */
export const Channel = {
  accounting: 'accounting',
  frontend: 'frontend',
  general: 'general',
  session: 'session',
} as const;

export type SettingChannel = (typeof Channel)[keyof typeof Channel];

/** The parsed channel object type behind each channel tag. */
export interface ChannelTypeMap {
  accounting: AccountingSettings;
  frontend: FrontendSettings;
  general: GeneralSettings;
  session: SessionSettings;
}

/**
 * The loose runtime view of a registry entry, used by the runtime helpers (`getRegistryEntry`, the
 * repo effect runner, the write dispatcher). The entries themselves are the precise `FieldDef` /
 * `ProjectedDef` the channel builders produce; this is what they all satisfy.
 */
export interface RegistryEntry {
  readonly channel: SettingChannel;
  readonly wireKey?: string;
  readonly encode?: (value: any) => unknown;
  readonly project?: (settings: any) => unknown;
  readonly userFacing?: boolean;
  readonly effects?: ReadonlyArray<(settings: any) => void>;
  readonly mirror?: () => Ref<any>;
  /** The settings-search anchor (`SettingsHighlightId`) this key scrolls to; many keys may share one. */
  readonly anchor?: SettingsHighlightId;
}

/** A setting backed by a real field on its channel object, identified by the typed wire key `W`. */
interface FieldDef<C extends SettingChannel, W extends string> {
  readonly channel: C;
  readonly wireKey: W;
  readonly encode?: (value: any) => unknown;
  readonly userFacing?: boolean;
  readonly effects?: ReadonlyArray<(settings: any) => void>;
  readonly mirror?: () => Ref<any>;
  readonly anchor?: SettingsHighlightId;
}

/** A read-only setting whose value is derived from the whole channel object (e.g. `currencySymbol`). */
interface ProjectedDef<C extends SettingChannel, V> {
  readonly channel: C;
  readonly project: (settings: any) => V;
  readonly userFacing?: boolean;
  readonly anchor?: SettingsHighlightId;
}

interface FieldOptions<T, W extends keyof T> {
  /** Transforms the read value to its wire type on write, when they differ (e.g. Currency -> ticker). */
  readonly encode?: (value: T[W]) => unknown;
  /** `false` = internal state, excluded from settings forms and search. */
  readonly userFacing?: boolean;
  /** Post-persist side effects run against the whole channel object after this key changes. */
  readonly effects?: ReadonlyArray<(settings: T) => void>;
  /** External shared ref kept in sync with this key's value after each write. */
  readonly mirror?: () => Ref<T[W]>;
  /** Settings-search anchor this key scrolls to (a `SettingsHighlightId`); composites share one. */
  readonly anchor?: SettingsHighlightId;
}

interface ProjectedOptions {
  readonly userFacing?: boolean;
  readonly anchor?: SettingsHighlightId;
}

/**
 * Per-channel entry builder. `channel('wireKey', opts)` declares a field-backed setting: the wire key
 * is constrained to `keyof ChannelSettings`, so a typo or a stale field name fails to compile, and
 * `encode`/`mirror`/`effects` are typed against that field's value. `channel.projected(fn)` declares a
 * read-only derived setting.
 */
interface ChannelBuilder<C extends SettingChannel> {
  <W extends keyof ChannelTypeMap[C] & string>(
    wireKey: W,
    options?: FieldOptions<ChannelTypeMap[C], W>,
  ): FieldDef<C, W>;
  readonly projected: <V>(
    project: (settings: ChannelTypeMap[C]) => V,
    options?: ProjectedOptions,
  ) => ProjectedDef<C, V>;
}

function defineChannel<C extends SettingChannel>(channel: C): ChannelBuilder<C> {
  type T = ChannelTypeMap[C];
  const field = <W extends keyof T & string>(wireKey: W, options: FieldOptions<T, W> = {}): FieldDef<C, W> => ({
    channel,
    wireKey,
    ...options,
  });
  const projected = <V>(project: (settings: T) => V, options: ProjectedOptions = {}): ProjectedDef<C, V> => ({
    channel,
    project,
    ...options,
  });
  return Object.assign(field, { projected });
}

const general = defineChannel(Channel.general);
const frontend = defineChannel(Channel.frontend);
const session = defineChannel(Channel.session);
const accounting = defineChannel(Channel.accounting);

/**
 * Single source of truth for every setting. Each entry is declared with its channel builder, which
 * validates the wire key against that channel's settings type at compile time (a typo or stale field
 * name fails to build) and types `encode`/`mirror`/`effects`/`project` against that field. `useSetting`
 * derives read routing, `settingsWriter` derives write routing, and `SettingValue` derives the value
 * type, all from here. Keys are grouped by channel, alphabetical within each group.
 */
export const settingsRegistry = {
  // general
  activeModules: general('activeModules'),
  addressNamePriority: general('addressNamePriority'),
  askUserUponSizeDiscrepancy: general('askUserUponSizeDiscrepancy', { anchor: SettingsHighlightIds.ASK_SIZE_DISCREPANCY }),
  assetMovementAmountTolerance: general('assetMovementAmountTolerance'),
  assetMovementTimeRange: general('assetMovementTimeRange'),
  autoCreateCalendarReminders: general('autoCreateCalendarReminders'),
  autoCreateProfitEvents: general('autoCreateProfitEvents', { anchor: SettingsHighlightIds.AUTO_CREATE_PROFIT_EVENTS }),
  autoDeleteCalendarEntries: general('autoDeleteCalendarEntries'),
  autoDetectTokens: general('autoDetectTokens', { anchor: SettingsHighlightIds.AUTO_DETECT_TOKENS }),
  balanceSaveFrequency: general('balanceSaveFrequency', { anchor: SettingsHighlightIds.BALANCE_SAVE_FREQUENCY }),
  beaconRpcEndpoint: general('beaconRpcEndpoint'),
  btcDerivationGapLimit: general('btcDerivationGapLimit', { anchor: SettingsHighlightIds.BTC_DERIVATION_GAP }),
  btcMempoolApi: general('btcMempoolApi'),
  connectTimeout: general('connectTimeout', { anchor: SettingsHighlightIds.CONNECT_TIMEOUT }),
  csvExportDelimiter: general('csvExportDelimiter', { anchor: SettingsHighlightIds.CSV_EXPORT }),
  currency: general('mainCurrency', { anchor: SettingsHighlightIds.AMOUNT_FORMAT, encode: value => value.tickerSymbol }),
  currencySymbol: general.projected(settings => settings.mainCurrency.tickerSymbol),
  currentPriceOracles: general('currentPriceOracles'),
  dateDisplayFormat: general('dateDisplayFormat', { anchor: SettingsHighlightIds.DATE_FORMAT }),
  defaultEvmIndexerOrder: general('defaultEvmIndexerOrder'),
  disabledChainQueries: general('disabledChainQueries', { anchor: SettingsHighlightIds.DISABLED_CHAIN_QUERIES }),
  displayDateInLocaltime: general('displayDateInLocaltime', { anchor: SettingsHighlightIds.DISPLAY_DATE_IN_LOCALTIME }),
  dotRpcEndpoint: general('dotRpcEndpoint'),
  evmIndexersOrder: general('evmIndexersOrder'),
  evmchainsToSkipDetection: general('evmchainsToSkipDetection', { anchor: SettingsHighlightIds.CHAINS_TO_SKIP_DETECTION }),
  floatingPrecision: general('uiFloatingPrecision', { anchor: SettingsHighlightIds.AMOUNT_FORMAT }),
  historicalPriceOracles: general('historicalPriceOracles'),
  inferZeroTimedBalances: general('inferZeroTimedBalances'),
  internalTxConflictRepullFrequency: general('internalTxConflictRepullFrequency', { anchor: SettingsHighlightIds.INTERNAL_TX_CONFLICT_REPULL }),
  internalTxsToRepull: general('internalTxsToRepull', { anchor: SettingsHighlightIds.INTERNAL_TX_CONFLICT_REPULL }),
  ksmRpcEndpoint: general('ksmRpcEndpoint'),
  nonSyncingExchanges: general('nonSyncingExchanges'),
  oraclePenaltyDuration: general('oraclePenaltyDuration', { anchor: SettingsHighlightIds.ORACLE_PENALTY_DURATION }),
  oraclePenaltyThresholdCount: general('oraclePenaltyThresholdCount', { anchor: SettingsHighlightIds.ORACLE_PENALTY_THRESHOLD }),
  queryRetryLimit: general('queryRetryLimit', { anchor: SettingsHighlightIds.QUERY_RETRY_LIMIT }),
  readTimeout: general('readTimeout', { anchor: SettingsHighlightIds.READ_TIMEOUT }),
  ssfGraphMultiplier: general('ssfGraphMultiplier'),
  submitUsageAnalytics: general('submitUsageAnalytics', { anchor: SettingsHighlightIds.USAGE_ANALYTICS }),
  suppressMissingKeyMsgServices: general('suppressMissingKeyMsgServices', { anchor: SettingsHighlightIds.SUPPRESS_MISSING_KEY }),
  treatEth2AsEth: general('treatEth2AsEth', { anchor: SettingsHighlightIds.TREAT_ETH2_AS_ETH }),
  // frontend
  abbreviateNumber: frontend('abbreviateNumber', { anchor: SettingsHighlightIds.ABBREVIATION }),
  amountRoundingMode: frontend('amountRoundingMode', { anchor: SettingsHighlightIds.ROUNDING }),
  autoDetectTokensCooldownHours: frontend('autoDetectTokensCooldownHours', { anchor: SettingsHighlightIds.AUTO_DETECT_TOKENS_COOLDOWN }),
  autoDetectTokensOnLogin: frontend('autoDetectTokensOnLogin', { anchor: SettingsHighlightIds.AUTO_DETECT_TOKENS_ON_LOGIN }),
  balanceValueThreshold: frontend('balanceValueThreshold'),
  blockchainRefreshButtonBehaviour: frontend('blockchainRefreshButtonBehaviour'),
  currencyLocation: frontend('currencyLocation', { anchor: SettingsHighlightIds.CURRENCY_LOCATION }),
  darkTheme: frontend('darkTheme'),
  dashboardTablesVisibleColumns: frontend('dashboardTablesVisibleColumns', { userFacing: false }),
  dateInputFormat: frontend('dateInputFormat'),
  decimalSeparator: frontend('decimalSeparator', { anchor: SettingsHighlightIds.AMOUNT_FORMAT, effects: [applyBigNumberFormat] }),
  defaultThemeVersion: frontend('defaultThemeVersion'),
  enableAliasNames: frontend('enableAliasNames'),
  enablePasswordConfirmation: frontend('enablePasswordConfirmation', { anchor: SettingsHighlightIds.PASSWORD_CONFIRMATION }),
  evmQueryIndicatorDismissalThreshold: frontend('evmQueryIndicatorDismissalThreshold', { anchor: SettingsHighlightIds.DISMISSAL_THRESHOLD }),
  evmQueryIndicatorMinOutOfSyncPeriod: frontend('evmQueryIndicatorMinOutOfSyncPeriod', { anchor: SettingsHighlightIds.MIN_OUT_OF_SYNC_PERIOD }),
  explorers: frontend('explorers', { anchor: SettingsHighlightIds.EXPLORERS }),
  gnosisPaySafeMigrationLastNotified: frontend('gnosisPaySafeMigrationLastNotified', { userFacing: false }),
  gnosisPaySafeMigrationNeverNotify: frontend('gnosisPaySafeMigrationNeverNotify'),
  graphZeroBased: frontend('graphZeroBased', { anchor: SettingsHighlightIds.GRAPH_BASIS }),
  ignoreSnapshotError: frontend('ignoreSnapshotError'),
  itemsPerPage: frontend('itemsPerPage', { mirror: useItemsPerPage }),
  language: frontend('language', { anchor: SettingsHighlightIds.LANGUAGE }),
  lastAppliedSettingsVersion: frontend('lastAppliedSettingsVersion', { userFacing: false }),
  lastAutoDetectAt: frontend('lastAutoDetectAt', { userFacing: false }),
  lastKnownTimeframe: frontend('lastKnownTimeframe', { userFacing: false }),
  lastPasswordConfirmed: frontend('lastPasswordConfirmed', { userFacing: false }),
  lightTheme: frontend('lightTheme'),
  minimumDigitToBeAbbreviated: frontend('minimumDigitToBeAbbreviated', { anchor: SettingsHighlightIds.ABBREVIATION }),
  newlyDetectedTokensMaxCount: frontend('newlyDetectedTokensMaxCount', { anchor: SettingsHighlightIds.NEWLY_DETECTED_TOKENS_MAX_COUNT }),
  newlyDetectedTokensTtlDays: frontend('newlyDetectedTokensTtlDays', { anchor: SettingsHighlightIds.NEWLY_DETECTED_TOKENS_TTL }),
  nftsInNetValue: frontend('nftsInNetValue', { anchor: SettingsHighlightIds.NFT_IN_NET_VALUE }),
  notifyNewNfts: frontend('notifyNewNfts', { anchor: SettingsHighlightIds.NFT_IMAGE_RENDERING }),
  passwordConfirmationInterval: frontend('passwordConfirmationInterval', { anchor: SettingsHighlightIds.PASSWORD_CONFIRMATION }),
  persistPrivacySettings: frontend('persistPrivacySettings', { anchor: SettingsHighlightIds.PERSIST_PRIVACY }),
  persistTableSorting: frontend('persistTableSorting', { anchor: SettingsHighlightIds.PERSIST_TABLE_SORTING }),
  privacyMode: frontend('privacyMode'),
  profitLossReportPeriod: frontend('profitLossReportPeriod'),
  queryPeriod: frontend('queryPeriod', { anchor: SettingsHighlightIds.PERIODIC_QUERY }),
  refreshPeriod: frontend('refreshPeriod', { anchor: SettingsHighlightIds.REFRESH_BALANCE }),
  renderAllNftImages: frontend('renderAllNftImages', { anchor: SettingsHighlightIds.NFT_IMAGE_RENDERING }),
  savedFilters: frontend('savedFilters', { userFacing: false }),
  scrambleData: frontend('scrambleData', { anchor: SettingsHighlightIds.SCRAMBLE }),
  scrambleMultiplier: frontend('scrambleMultiplier', { anchor: SettingsHighlightIds.SCRAMBLE }),
  selectedTheme: frontend('selectedTheme'),
  shouldShowAmount: frontend.projected(settings => settings.privacyMode < PrivacyMode.SEMI_PRIVATE),
  shouldShowPercentage: frontend.projected(settings => settings.privacyMode < PrivacyMode.PRIVATE),
  showGraphRangeSelector: frontend('showGraphRangeSelector'),
  subscriptDecimals: frontend('subscriptDecimals', { anchor: SettingsHighlightIds.SUBSCRIPT }),
  suppressNoIndexerChains: frontend('suppressNoIndexerChains', { anchor: SettingsHighlightIds.SUPPRESSED_NO_INDEXER_CHAINS }),
  thousandSeparator: frontend('thousandSeparator', { anchor: SettingsHighlightIds.AMOUNT_FORMAT, effects: [applyBigNumberFormat] }),
  timeframeSetting: frontend('timeframeSetting', { anchor: SettingsHighlightIds.TIMEFRAME }),
  useHistoricalAssetBalances: frontend('useHistoricalAssetBalances'),
  valueRoundingMode: frontend('valueRoundingMode', { anchor: SettingsHighlightIds.ROUNDING }),
  versionUpdateCheckFrequency: frontend('versionUpdateCheckFrequency', { anchor: SettingsHighlightIds.VERSION_UPDATE_CHECK }),
  visibleTimeframes: frontend('visibleTimeframes', { anchor: SettingsHighlightIds.TIMEFRAME }),
  whitelistedDomainsForNftImages: frontend('whitelistedDomainsForNftImages', { anchor: SettingsHighlightIds.NFT_IMAGE_RENDERING }),
  // session
  animationsEnabled: session('animationsEnabled', { anchor: SettingsHighlightIds.ANIMATIONS, mirror: useAnimationsEnabled }),
  timeframe: session('timeframe'),
  // accounting
  calculatePastCostBasis: accounting('calculatePastCostBasis', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  costBasisMethod: accounting('costBasisMethod', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  ethStakingTaxableAfterWithdrawalEnabled: accounting('ethStakingTaxableAfterWithdrawalEnabled', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  includeCrypto2crypto: accounting('includeCrypto2crypto', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  includeFeesInCostBasis: accounting('includeFeesInCostBasis', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  includeGasCosts: accounting('includeGasCosts', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  pnlCsvHaveSummary: accounting('pnlCsvHaveSummary', { anchor: SettingsHighlightIds.CSV_EXPORT }),
  pnlCsvWithFormulas: accounting('pnlCsvWithFormulas', { anchor: SettingsHighlightIds.CSV_EXPORT }),
  taxfreeAfterPeriod: accounting('taxfreeAfterPeriod', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
  useAssetCollectionsInCostBasis: accounting('useAssetCollectionsInCostBasis', { anchor: SettingsHighlightIds.ACCOUNTING_TRADE }),
} satisfies Record<string, RegistryEntry>;

/**
 * Registry keyed for dynamic (unregistered-key-tolerant) lookup. A `Map` built from `Object.entries`
 * types its values as `RegistryEntry` without any assertion, so consumers that resolve an entry from
 * an arbitrary `string` (the write dispatcher, the repo's effect runner) go through here instead of
 * casting `settingsRegistry` to a `Record` at each call site.
 */
const registryByKey: ReadonlyMap<string, RegistryEntry> = new Map(Object.entries(settingsRegistry));

/** Resolves a registry entry from an arbitrary string key, or `undefined` if the key is not registered. */
export function getRegistryEntry(key: string): RegistryEntry | undefined {
  return registryByKey.get(key);
}

/** All registry entries as typed `[logicalKey, entry]` pairs (a bare `Object.entries` widens to a union). */
export function registryEntries(): ReadonlyArray<readonly [string, RegistryEntry]> {
  return [...registryByKey];
}

/**
 * Reverse index: the logical keys that share a given settings-search anchor. Built once from the
 * registry so it cannot drift; composite anchors return several keys, keyless anchors return `[]`.
 */
const keysByAnchor: ReadonlyMap<SettingsHighlightId, readonly string[]> = ((): ReadonlyMap<SettingsHighlightId, readonly string[]> => {
  const map = new Map<SettingsHighlightId, string[]>();
  for (const [key, entry] of registryByKey) {
    const { anchor } = entry;
    if (!anchor)
      continue;
    const keys = map.get(anchor) ?? [];
    keys.push(key);
    map.set(anchor, keys);
  }
  return map;
})();

/** The registry keys anchored to `anchor` (empty for keyless anchors such as action targets). */
export function registryKeysForAnchor(anchor: SettingsHighlightId): readonly string[] {
  return keysByAnchor.get(anchor) ?? [];
}
