import type { Ref } from 'vue';
import type { FrontendSettings } from '@/modules/settings/types/frontend-settings';
import type { AccountingSettings, GeneralSettings } from '@/modules/settings/types/user-settings';
import { BigNumber } from '@rotki/common';
import { getBnFormat } from '@/modules/assets/amount-display/amount-formatter';
import { PrivacyMode, type SessionSettings } from '@/modules/session/types';
import { useAnimationsEnabled } from '@/modules/session/use-animations-enabled';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';

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
}

/** A setting backed by a real field on its channel object, identified by the typed wire key `W`. */
interface FieldDef<C extends SettingChannel, W extends string> {
  readonly channel: C;
  readonly wireKey: W;
  readonly encode?: (value: any) => unknown;
  readonly userFacing?: boolean;
  readonly effects?: ReadonlyArray<(settings: any) => void>;
  readonly mirror?: () => Ref<any>;
}

/** A read-only setting whose value is derived from the whole channel object (e.g. `currencySymbol`). */
interface ProjectedDef<C extends SettingChannel, V> {
  readonly channel: C;
  readonly project: (settings: any) => V;
  readonly userFacing?: boolean;
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
}

interface ProjectedOptions {
  readonly userFacing?: boolean;
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
  askUserUponSizeDiscrepancy: general('askUserUponSizeDiscrepancy'),
  assetMovementAmountTolerance: general('assetMovementAmountTolerance'),
  assetMovementTimeRange: general('assetMovementTimeRange'),
  autoCreateCalendarReminders: general('autoCreateCalendarReminders'),
  autoCreateProfitEvents: general('autoCreateProfitEvents'),
  autoDeleteCalendarEntries: general('autoDeleteCalendarEntries'),
  autoDetectTokens: general('autoDetectTokens'),
  balanceSaveFrequency: general('balanceSaveFrequency'),
  beaconRpcEndpoint: general('beaconRpcEndpoint'),
  btcDerivationGapLimit: general('btcDerivationGapLimit'),
  btcMempoolApi: general('btcMempoolApi'),
  connectTimeout: general('connectTimeout'),
  csvExportDelimiter: general('csvExportDelimiter'),
  currency: general('mainCurrency', { encode: value => value.tickerSymbol }),
  currencySymbol: general.projected(settings => settings.mainCurrency.tickerSymbol),
  currentPriceOracles: general('currentPriceOracles'),
  dateDisplayFormat: general('dateDisplayFormat'),
  defaultEvmIndexerOrder: general('defaultEvmIndexerOrder'),
  disabledChainQueries: general('disabledChainQueries'),
  displayDateInLocaltime: general('displayDateInLocaltime'),
  dotRpcEndpoint: general('dotRpcEndpoint'),
  evmIndexersOrder: general('evmIndexersOrder'),
  evmchainsToSkipDetection: general('evmchainsToSkipDetection'),
  floatingPrecision: general('uiFloatingPrecision'),
  historicalPriceOracles: general('historicalPriceOracles'),
  inferZeroTimedBalances: general('inferZeroTimedBalances'),
  internalTxConflictRepullFrequency: general('internalTxConflictRepullFrequency'),
  internalTxsToRepull: general('internalTxsToRepull'),
  ksmRpcEndpoint: general('ksmRpcEndpoint'),
  nonSyncingExchanges: general('nonSyncingExchanges'),
  oraclePenaltyDuration: general('oraclePenaltyDuration'),
  oraclePenaltyThresholdCount: general('oraclePenaltyThresholdCount'),
  queryRetryLimit: general('queryRetryLimit'),
  readTimeout: general('readTimeout'),
  ssfGraphMultiplier: general('ssfGraphMultiplier'),
  submitUsageAnalytics: general('submitUsageAnalytics'),
  suppressMissingKeyMsgServices: general('suppressMissingKeyMsgServices'),
  treatEth2AsEth: general('treatEth2AsEth'),
  // frontend
  abbreviateNumber: frontend('abbreviateNumber'),
  amountRoundingMode: frontend('amountRoundingMode'),
  autoDetectTokensCooldownHours: frontend('autoDetectTokensCooldownHours'),
  autoDetectTokensOnLogin: frontend('autoDetectTokensOnLogin'),
  balanceValueThreshold: frontend('balanceValueThreshold'),
  blockchainRefreshButtonBehaviour: frontend('blockchainRefreshButtonBehaviour'),
  currencyLocation: frontend('currencyLocation'),
  darkTheme: frontend('darkTheme'),
  dashboardTablesVisibleColumns: frontend('dashboardTablesVisibleColumns', { userFacing: false }),
  dateInputFormat: frontend('dateInputFormat'),
  decimalSeparator: frontend('decimalSeparator', { effects: [applyBigNumberFormat] }),
  defaultThemeVersion: frontend('defaultThemeVersion'),
  enableAliasNames: frontend('enableAliasNames'),
  enablePasswordConfirmation: frontend('enablePasswordConfirmation'),
  evmQueryIndicatorDismissalThreshold: frontend('evmQueryIndicatorDismissalThreshold'),
  evmQueryIndicatorMinOutOfSyncPeriod: frontend('evmQueryIndicatorMinOutOfSyncPeriod'),
  explorers: frontend('explorers'),
  gnosisPaySafeMigrationLastNotified: frontend('gnosisPaySafeMigrationLastNotified', { userFacing: false }),
  gnosisPaySafeMigrationNeverNotify: frontend('gnosisPaySafeMigrationNeverNotify'),
  graphZeroBased: frontend('graphZeroBased'),
  ignoreSnapshotError: frontend('ignoreSnapshotError'),
  itemsPerPage: frontend('itemsPerPage', { mirror: useItemsPerPage }),
  language: frontend('language'),
  lastAppliedSettingsVersion: frontend('lastAppliedSettingsVersion', { userFacing: false }),
  lastAutoDetectAt: frontend('lastAutoDetectAt', { userFacing: false }),
  lastKnownTimeframe: frontend('lastKnownTimeframe', { userFacing: false }),
  lastPasswordConfirmed: frontend('lastPasswordConfirmed', { userFacing: false }),
  lightTheme: frontend('lightTheme'),
  minimumDigitToBeAbbreviated: frontend('minimumDigitToBeAbbreviated'),
  newlyDetectedTokensMaxCount: frontend('newlyDetectedTokensMaxCount'),
  newlyDetectedTokensTtlDays: frontend('newlyDetectedTokensTtlDays'),
  nftsInNetValue: frontend('nftsInNetValue'),
  notifyNewNfts: frontend('notifyNewNfts'),
  passwordConfirmationInterval: frontend('passwordConfirmationInterval'),
  persistPrivacySettings: frontend('persistPrivacySettings'),
  persistTableSorting: frontend('persistTableSorting'),
  privacyMode: frontend('privacyMode'),
  profitLossReportPeriod: frontend('profitLossReportPeriod'),
  queryPeriod: frontend('queryPeriod'),
  refreshPeriod: frontend('refreshPeriod'),
  renderAllNftImages: frontend('renderAllNftImages'),
  savedFilters: frontend('savedFilters', { userFacing: false }),
  scrambleData: frontend('scrambleData'),
  scrambleMultiplier: frontend('scrambleMultiplier'),
  selectedTheme: frontend('selectedTheme'),
  shouldShowAmount: frontend.projected(settings => settings.privacyMode < PrivacyMode.SEMI_PRIVATE),
  shouldShowPercentage: frontend.projected(settings => settings.privacyMode < PrivacyMode.PRIVATE),
  showGraphRangeSelector: frontend('showGraphRangeSelector'),
  subscriptDecimals: frontend('subscriptDecimals'),
  suppressNoIndexerChains: frontend('suppressNoIndexerChains'),
  thousandSeparator: frontend('thousandSeparator', { effects: [applyBigNumberFormat] }),
  timeframeSetting: frontend('timeframeSetting'),
  useHistoricalAssetBalances: frontend('useHistoricalAssetBalances'),
  valueRoundingMode: frontend('valueRoundingMode'),
  versionUpdateCheckFrequency: frontend('versionUpdateCheckFrequency'),
  visibleTimeframes: frontend('visibleTimeframes'),
  whitelistedDomainsForNftImages: frontend('whitelistedDomainsForNftImages'),
  // session
  animationsEnabled: session('animationsEnabled', { mirror: useAnimationsEnabled }),
  timeframe: session('timeframe'),
  // accounting
  calculatePastCostBasis: accounting('calculatePastCostBasis'),
  costBasisMethod: accounting('costBasisMethod'),
  ethStakingTaxableAfterWithdrawalEnabled: accounting('ethStakingTaxableAfterWithdrawalEnabled'),
  includeCrypto2crypto: accounting('includeCrypto2crypto'),
  includeFeesInCostBasis: accounting('includeFeesInCostBasis'),
  includeGasCosts: accounting('includeGasCosts'),
  pnlCsvHaveSummary: accounting('pnlCsvHaveSummary'),
  pnlCsvWithFormulas: accounting('pnlCsvWithFormulas'),
  taxfreeAfterPeriod: accounting('taxfreeAfterPeriod'),
  useAssetCollectionsInCostBasis: accounting('useAssetCollectionsInCostBasis'),
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
