import type { ActionStatus } from '@/types/action';
import { assert, BigNumber } from '@rotki/common';
import { useSettingsApi } from '@/composables/api/settings/settings-api';
import { useItemsPerPage } from '@/composables/session/use-items-per-page';
import { useComputedRef } from '@/composables/utils/useComputedRef';
import { getBnFormat } from '@/data/amount-formatter';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { PrivacyMode } from '@/types/session';
import {
  type FrontendSettings,
  type FrontendSettingsPayload,
  getDefaultFrontendSettings,
} from '@/types/settings/frontend-settings';
import { logger } from '@/utils/logging';

export const useFrontendSettingsStore = defineStore('settings/frontend', () => {
  const settings = ref<FrontendSettings>(markRaw(getDefaultFrontendSettings()));

  const defiSetupDone = useComputedRef(settings, 'defiSetupDone');
  const language = useComputedRef(settings, 'language');
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
  const blockchainRefreshButtonBehaviour = useComputedRef(settings, 'blockchainRefreshButtonBehaviour');
  const savedFilters = useComputedRef(settings, 'savedFilters');
  const balanceUsdValueThreshold = useComputedRef(settings, 'balanceUsdValueThreshold');
  const useHistoricalAssetBalances = useComputedRef(settings, 'useHistoricalAssetBalances');
  const notifyNewNfts = useComputedRef(settings, 'notifyNewNfts');
  const persistPrivacySettings = useComputedRef(settings, 'persistPrivacySettings');
  const privacyMode = useComputedRef(settings, 'privacyMode');
  const scrambleData = useComputedRef(settings, 'scrambleData');
  const scrambleMultiplier = useComputedRef(settings, 'scrambleMultiplier');
  const evmQueryIndicatorMinOutOfSyncPeriod = useComputedRef(settings, 'evmQueryIndicatorMinOutOfSyncPeriod');
  const evmQueryIndicatorDismissalThreshold = useComputedRef(settings, 'evmQueryIndicatorDismissalThreshold');

  const shouldShowAmount = computed(() => get(privacyMode) < PrivacyMode.SEMI_PRIVATE);
  const shouldShowPercentage = computed(() => get(privacyMode) < PrivacyMode.PRIVATE);

  const globalItemsPerPage = useItemsPerPage();

  const api = useSettingsApi();

  function update(update: FrontendSettings): void {
    set(settings, {
      ...get(settings),
      ...update,
    });
    const itemsPerPage = get(settings, 'itemsPerPage');
    if (itemsPerPage !== get(globalItemsPerPage))
      set(globalItemsPerPage, itemsPerPage);
  }

  async function updateSetting(payload: FrontendSettingsPayload): Promise<ActionStatus> {
    const props = Object.keys(payload);
    assert(props.length > 0, 'Payload must be not-empty');
    try {
      const updatedSettings = { ...get(settings), ...payload };
      const { other } = await api.setSettings({
        frontendSettings: JSON.stringify(snakeCaseTransformer(updatedSettings)),
      });

      update(updatedSettings);

      if (payload.thousandSeparator || payload.decimalSeparator) {
        BigNumber.config({
          FORMAT: getBnFormat(other.frontendSettings.thousandSeparator, other.frontendSettings.decimalSeparator),
        });
      }

      return {
        success: true,
      };
    }
    catch (error: any) {
      logger.error(error);
      return {
        message: error.message,
        success: false,
      };
    }
  }

  watchDebounced(globalItemsPerPage, async (value, oldValue) => {
    if (oldValue === undefined || value === oldValue)
      return;

    try {
      await updateSetting({ itemsPerPage: value });
    }
    catch (error: any) {
      logger.error(error);
    }
  }, { debounce: 800, maxWait: 1200 });

  return {
    abbreviateNumber,
    amountRoundingMode,
    balanceUsdValueThreshold,
    blockchainRefreshButtonBehaviour,
    currencyLocation,
    darkTheme,
    dashboardTablesVisibleColumns,
    dateInputFormat,
    decimalSeparator,
    defaultThemeVersion,
    defiSetupDone,
    enableAliasNames,
    evmQueryIndicatorDismissalThreshold,
    evmQueryIndicatorMinOutOfSyncPeriod,
    explorers,
    graphZeroBased,
    ignoreSnapshotError,
    itemsPerPage,
    language,
    lastKnownTimeframe,
    lightTheme,
    minimumDigitToBeAbbreviated,
    nftsInNetValue,
    notifyNewNfts,
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
    subscriptDecimals,
    thousandSeparator,
    timeframeSetting,
    update,
    updateSetting,
    useHistoricalAssetBalances,
    valueRoundingMode,
    versionUpdateCheckFrequency,
    visibleTimeframes,
    whitelistedDomainsForNftImages,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useFrontendSettingsStore, import.meta.hot));
