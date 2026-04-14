import type { PendingSuggestion } from '@/modules/settings/suggestions/settings-suggestions';
import { useItemsPerPage } from '@/composables/session/use-items-per-page';
import { useComputedRef } from '@/composables/utils/useComputedRef';
import { PrivacyMode } from '@/types/session';
import {
  type FrontendSettings,
  getDefaultFrontendSettings,
} from '@/types/settings/frontend-settings';

export const useFrontendSettingsStore = defineStore('settings/frontend', () => {
  const settings = ref<FrontendSettings>(markRaw(getDefaultFrontendSettings()));

  const defiSetupDone = useComputedRef(settings, 'defiSetupDone');
  const enablePasswordConfirmation = useComputedRef(settings, 'enablePasswordConfirmation');
  const language = useComputedRef(settings, 'language');
  const lastAppliedSettingsVersion = useComputedRef(settings, 'lastAppliedSettingsVersion');
  const timeframeSetting = useComputedRef(settings, 'timeframeSetting');
  const visibleTimeframes = useComputedRef(settings, 'visibleTimeframes');
  const lastKnownTimeframe = useComputedRef(settings, 'lastKnownTimeframe');
  const queryPeriod = useComputedRef(settings, 'queryPeriod');
  const profitLossReportPeriod = useComputedRef(settings, 'profitLossReportPeriod');
  const thousandSeparator = useComputedRef(settings, 'thousandSeparator');
  const decimalSeparator = useComputedRef(settings, 'decimalSeparator');
  const currencyLocation = useComputedRef(settings, 'currencyLocation');
  const abbreviateNumber = useComputedRef(settings, 'abbreviateNumber');
  const minimumDigitToBeAbbreviated = useComputedRef(settings, 'minimumDigitToBeAbbreviated');
  const newlyDetectedTokensMaxCount = useComputedRef(settings, 'newlyDetectedTokensMaxCount');
  const newlyDetectedTokensTtlDays = useComputedRef(settings, 'newlyDetectedTokensTtlDays');
  const refreshPeriod = useComputedRef(settings, 'refreshPeriod');
  const explorers = useComputedRef(settings, 'explorers');
  const itemsPerPage = useComputedRef(settings, 'itemsPerPage');
  const amountRoundingMode = useComputedRef(settings, 'amountRoundingMode');
  const valueRoundingMode = useComputedRef(settings, 'valueRoundingMode');
  const subscriptDecimals = useComputedRef(settings, 'subscriptDecimals');
  const selectedTheme = useComputedRef(settings, 'selectedTheme');
  const lightTheme = useComputedRef(settings, 'lightTheme');
  const darkTheme = useComputedRef(settings, 'darkTheme');
  const defaultThemeVersion = useComputedRef(settings, 'defaultThemeVersion');
  const graphZeroBased = useComputedRef(settings, 'graphZeroBased');
  const ignoreSnapshotError = useComputedRef(settings, 'ignoreSnapshotError');
  const showGraphRangeSelector = useComputedRef(settings, 'showGraphRangeSelector');
  const nftsInNetValue = useComputedRef(settings, 'nftsInNetValue');
  const persistTableSorting = useComputedRef(settings, 'persistTableSorting');
  const renderAllNftImages = useComputedRef(settings, 'renderAllNftImages');
  const whitelistedDomainsForNftImages = useComputedRef(settings, 'whitelistedDomainsForNftImages');
  const dashboardTablesVisibleColumns = useComputedRef(settings, 'dashboardTablesVisibleColumns');
  const dateInputFormat = useComputedRef(settings, 'dateInputFormat');
  const versionUpdateCheckFrequency = useComputedRef(settings, 'versionUpdateCheckFrequency');
  const enableAliasNames = useComputedRef(settings, 'enableAliasNames');
  const blockchainRefreshButtonBehaviour = useComputedRef(
    settings,
    'blockchainRefreshButtonBehaviour',
  );
  const savedFilters = useComputedRef(settings, 'savedFilters');
  const balanceValueThreshold = useComputedRef(settings, 'balanceValueThreshold');
  const useHistoricalAssetBalances = useComputedRef(settings, 'useHistoricalAssetBalances');
  const notifyNewNfts = useComputedRef(settings, 'notifyNewNfts');
  const persistPrivacySettings = useComputedRef(settings, 'persistPrivacySettings');
  const privacyMode = useComputedRef(settings, 'privacyMode');
  const scrambleData = useComputedRef(settings, 'scrambleData');
  const scrambleMultiplier = useComputedRef(settings, 'scrambleMultiplier');
  const evmQueryIndicatorMinOutOfSyncPeriod = useComputedRef(
    settings,
    'evmQueryIndicatorMinOutOfSyncPeriod',
  );
  const evmQueryIndicatorDismissalThreshold = useComputedRef(
    settings,
    'evmQueryIndicatorDismissalThreshold',
  );
  const lastPasswordConfirmed = useComputedRef(settings, 'lastPasswordConfirmed');
  const passwordConfirmationInterval = useComputedRef(settings, 'passwordConfirmationInterval');

  const shouldShowAmount = computed(() => get(privacyMode) < PrivacyMode.SEMI_PRIVATE);
  const shouldShowPercentage = computed(() => get(privacyMode) < PrivacyMode.PRIVATE);

  const pendingSuggestions = ref<PendingSuggestion[]>([]);
  const showSuggestionsDialog = shallowRef<boolean>(false);

  const globalItemsPerPage = useItemsPerPage();

  function update(update: Partial<FrontendSettings>): void {
    set(settings, {
      ...get(settings),
      ...update,
    });
    const itemsPerPage = get(settings, 'itemsPerPage');
    if (itemsPerPage !== get(globalItemsPerPage))
      set(globalItemsPerPage, itemsPerPage);
  }

  return {
    abbreviateNumber,
    amountRoundingMode,
    balanceValueThreshold,
    blockchainRefreshButtonBehaviour,
    currencyLocation,
    darkTheme,
    dashboardTablesVisibleColumns,
    dateInputFormat,
    decimalSeparator,
    defaultThemeVersion,
    defiSetupDone,
    enableAliasNames,
    enablePasswordConfirmation,
    evmQueryIndicatorDismissalThreshold,
    evmQueryIndicatorMinOutOfSyncPeriod,
    explorers,
    graphZeroBased,
    ignoreSnapshotError,
    itemsPerPage,
    language,
    lastAppliedSettingsVersion,
    lastKnownTimeframe,
    lastPasswordConfirmed,
    lightTheme,
    minimumDigitToBeAbbreviated,
    newlyDetectedTokensMaxCount,
    newlyDetectedTokensTtlDays,
    nftsInNetValue,
    notifyNewNfts,
    passwordConfirmationInterval,
    pendingSuggestions,
    persistPrivacySettings,
    persistTableSorting,
    privacyMode,
    profitLossReportPeriod,
    queryPeriod,
    refreshPeriod,
    renderAllNftImages,
    savedFilters,
    scrambleData,
    scrambleMultiplier,
    selectedTheme,
    settings,
    shouldShowAmount,
    shouldShowPercentage,
    showGraphRangeSelector,
    showSuggestionsDialog,
    subscriptDecimals,
    thousandSeparator,
    timeframeSetting,
    update,
    useHistoricalAssetBalances,
    valueRoundingMode,
    versionUpdateCheckFrequency,
    visibleTimeframes,
    whitelistedDomainsForNftImages,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useFrontendSettingsStore, import.meta.hot));
