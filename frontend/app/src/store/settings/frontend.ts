import { BigNumber } from '@rotki/common';
import { getBnFormat } from '@/data/amount-formatter';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import {
  FrontendSettings,
  type FrontendSettingsPayload,
} from '@/types/settings/frontend-settings';
import type { ActionStatus } from '@/types/action';

export const useFrontendSettingsStore = defineStore('settings/frontend', () => {
  const settings = ref<FrontendSettings>(markRaw(FrontendSettings.parse({})));

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
  const selectedTheme = useComputedRef(settings, 'selectedTheme');
  const lightTheme = useComputedRef(settings, 'lightTheme');
  const darkTheme = useComputedRef(settings, 'darkTheme');
  const defaultThemeVersion = useComputedRef(settings, 'defaultThemeVersion');
  const graphZeroBased = useComputedRef(settings, 'graphZeroBased');
  const showGraphRangeSelector = useComputedRef(settings, 'showGraphRangeSelector');
  const nftsInNetValue = useComputedRef(settings, 'nftsInNetValue');
  const renderAllNftImages = useComputedRef(settings, 'renderAllNftImages');
  const whitelistedDomainsForNftImages = useComputedRef(settings, 'whitelistedDomainsForNftImages');
  const dashboardTablesVisibleColumns = useComputedRef(settings, 'dashboardTablesVisibleColumns');
  const dateInputFormat = useComputedRef(settings, 'dateInputFormat');
  const versionUpdateCheckFrequency = useComputedRef(settings, 'versionUpdateCheckFrequency');
  const enableAliasNames = useComputedRef(settings, 'enableAliasNames');
  const blockchainRefreshButtonBehaviour = useComputedRef(settings, 'blockchainRefreshButtonBehaviour');
  const shouldRefreshValidatorDailyStats = useComputedRef(settings, 'shouldRefreshValidatorDailyStats');
  const unifyAccountsTable = useComputedRef(settings, 'unifyAccountsTable');
  const savedFilters = useComputedRef(settings, 'savedFilters');

  const globalItemsPerPage = useItemsPerPage();

  const api = useSettingsApi();
  const { checkMachineLanguage, forceUpdateMachineLanguage } = useLastLanguage();

  function update(update: FrontendSettings): void {
    set(settings, {
      ...get(settings),
      ...update,
    });
    checkMachineLanguage(language);
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
      return {
        success: false,
        message: error.message,
      };
    }
  }

  watch([language, forceUpdateMachineLanguage], () => {
    checkMachineLanguage(get(language));
  });

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
    defiSetupDone,
    language,
    timeframeSetting,
    visibleTimeframes,
    lastKnownTimeframe,
    queryPeriod,
    profitLossReportPeriod,
    thousandSeparator,
    decimalSeparator,
    currencyLocation,
    abbreviateNumber,
    defaultThemeVersion,
    minimumDigitToBeAbbreviated,
    refreshPeriod,
    explorers,
    itemsPerPage,
    amountRoundingMode,
    valueRoundingMode,
    selectedTheme,
    lightTheme,
    darkTheme,
    graphZeroBased,
    showGraphRangeSelector,
    nftsInNetValue,
    renderAllNftImages,
    whitelistedDomainsForNftImages,
    dashboardTablesVisibleColumns,
    dateInputFormat,
    versionUpdateCheckFrequency,
    enableAliasNames,
    blockchainRefreshButtonBehaviour,
    shouldRefreshValidatorDailyStats,
    unifyAccountsTable,
    savedFilters,
    settings,
    updateSetting,
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useFrontendSettingsStore, import.meta.hot));
