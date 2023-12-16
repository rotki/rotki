import { BigNumber } from '@rotki/common';
import { type Theme, ThemeColors } from '@rotki/common/lib/settings';
import { isUndefined } from 'lodash-es';
import { getBnFormat } from '@/data/amount-formatter';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import {
  type BlockchainRefreshButtonBehaviour,
  type DashboardTablesVisibleColumns,
  type ExplorersSettings,
  FrontendSettings,
  type FrontendSettingsPayload,
  type ProfitLossTimeframe,
  type RefreshPeriod,
  type RoundingMode,
  SupportedLanguage,
} from '@/types/settings/frontend-settings';
import { CURRENT_DEFAULT_THEME_VERSION, DARK_COLORS, DEFAULT_THEME_HISTORIES, LIGHT_COLORS } from '@/plugins/theme';
import type { TimeFramePeriod, TimeFrameSetting } from '@rotki/common/lib/settings/graphs';
import type { CurrencyLocation } from '@/types/currency-location';
import type { DateFormat } from '@/types/date-format';
import type { ActionStatus } from '@/types/action';
import type { BaseSuggestion, SavedFilterLocation } from '@/types/filtering';

export const useFrontendSettingsStore = defineStore('settings/frontend', () => {
  const settings = reactive(FrontendSettings.parse({}));
  const defiSetupDone = computed<boolean>(() => settings.defiSetupDone);
  const language = computed<SupportedLanguage>(() => settings.language);
  const timeframeSetting = computed<TimeFrameSetting>(() => settings.timeframeSetting);
  const visibleTimeframes = computed<TimeFrameSetting[]>(() => settings.visibleTimeframes);
  const lastKnownTimeframe = computed<TimeFramePeriod>(() => settings.lastKnownTimeframe);
  const queryPeriod = computed<number>(() => settings.queryPeriod);
  const profitLossReportPeriod = computed<ProfitLossTimeframe>(() => settings.profitLossReportPeriod);
  const thousandSeparator = computed<string>(() => settings.thousandSeparator);
  const decimalSeparator = computed<string>(() => settings.decimalSeparator);
  const currencyLocation = computed<CurrencyLocation>(() => settings.currencyLocation);
  const abbreviateNumber = computed<boolean>(() => settings.abbreviateNumber);
  const minimumDigitToBeAbbreviated = computed<number>(() => settings.minimumDigitToBeAbbreviated);
  const refreshPeriod = computed<RefreshPeriod>(() => settings.refreshPeriod);
  const explorers = computed<ExplorersSettings>(() => settings.explorers);
  const itemsPerPage = computed<number>({
    get: () => settings.itemsPerPage,
    set: (value: number) => {
      settings.itemsPerPage = value;
    },
  });
  const amountRoundingMode = computed<RoundingMode>(() => settings.amountRoundingMode);
  const valueRoundingMode = computed<RoundingMode>(() => settings.valueRoundingMode);
  const selectedTheme = computed<Theme>(() => settings.selectedTheme);
  const lightTheme = computed<ThemeColors>(() => settings.lightTheme);
  const darkTheme = computed<ThemeColors>(() => settings.darkTheme);
  const defaultThemeVersion = computed<number>(() => settings.defaultThemeVersion);
  const graphZeroBased = computed<boolean>(() => settings.graphZeroBased);
  const showGraphRangeSelector = computed<boolean>(() => settings.showGraphRangeSelector);
  const nftsInNetValue = computed<boolean>(() => settings.nftsInNetValue);
  const renderAllNftImages = computed<boolean>(() => settings.renderAllNftImages);
  const whitelistedDomainsForNftImages = computed<string[]>(() => settings.whitelistedDomainsForNftImages);
  const dashboardTablesVisibleColumns = computed<DashboardTablesVisibleColumns>(
    () => settings.dashboardTablesVisibleColumns,
  );
  const dateInputFormat = computed<DateFormat>(() => settings.dateInputFormat);
  const versionUpdateCheckFrequency = computed<number>(() => settings.versionUpdateCheckFrequency);
  const enableAliasNames = computed<boolean>(() => settings.enableAliasNames);
  const blockchainRefreshButtonBehaviour = computed<BlockchainRefreshButtonBehaviour>(
    () => settings.blockchainRefreshButtonBehaviour,
  );
  const shouldRefreshValidatorDailyStats = computed<boolean>(
    () => settings.shouldRefreshValidatorDailyStats,
  );

  const savedFilters = computed<{
    [key in SavedFilterLocation]?: BaseSuggestion[][];
  }>(() => settings.savedFilters);

  const api = useSettingsApi();

  const { lastLanguage, forceUpdateMachineLanguage } = useLastLanguage();

  const checkMachineLanguage = (): void => {
    if (get(forceUpdateMachineLanguage) === 'true')
      set(lastLanguage, get(language));
    else set(lastLanguage, SupportedLanguage.EN);
  };

  const update = (update: FrontendSettings): void => {
    Object.assign(settings, update);
    checkMachineLanguage();
  };

  async function updateSetting(payload: FrontendSettingsPayload): Promise<ActionStatus> {
    const props = Object.keys(payload);
    assert(props.length > 0, 'Payload must be not-empty');
    try {
      const updatedSettings = { ...settings, ...payload };
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
    checkMachineLanguage();
  });

  watchDebounced(
    itemsPerPage,
    (value, oldValue) => {
      if (isUndefined(oldValue) || value === oldValue)
        return;

      updateSetting({ itemsPerPage: value }).catch(error => logger.debug(error));
    },
    { debounce: 100 },
  );

  const checkDefaultThemeVersion = () => {
    const defaultThemeVersionSetting = get(defaultThemeVersion);
    if (defaultThemeVersionSetting < CURRENT_DEFAULT_THEME_VERSION) {
      const historicDefaultTheme = DEFAULT_THEME_HISTORIES.find(
        ({ version }) => version === defaultThemeVersionSetting,
      );

      if (historicDefaultTheme) {
        const newLightTheme: ThemeColors = { ...LIGHT_COLORS };
        const newDarkTheme: ThemeColors = { ...DARK_COLORS };
        const savedLightTheme = get(lightTheme);
        const savedDarkTheme = get(darkTheme);

        const accentColors = Object.keys(ThemeColors.shape);

        const isKeyOfThemeColors = (key: string): key is keyof ThemeColors => accentColors.includes(key);

        accentColors.forEach((key) => {
          if (!isKeyOfThemeColors(key))
            return;

          // If saved theme isn't the same with the default theme at that version, do not replace with new default.
          if (historicDefaultTheme.lightColors[key] !== savedLightTheme[key])
            newLightTheme[key] = savedLightTheme[key];

          if (historicDefaultTheme.darkColors[key] !== savedDarkTheme[key])
            newDarkTheme[key] = savedDarkTheme[key];
        });

        startPromise(
          updateSetting({
            lightTheme: newLightTheme,
            darkTheme: newDarkTheme,
            defaultThemeVersion: CURRENT_DEFAULT_THEME_VERSION,
          }),
        );
      }
    }
  };

  return {
    forceUpdateMachineLanguage,
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
    savedFilters,
    // return settings on development for state persistence
    ...(checkIfDevelopment() ? { settings } : {}),
    updateSetting,
    update,
    checkDefaultThemeVersion,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useFrontendSettingsStore, import.meta.hot));
