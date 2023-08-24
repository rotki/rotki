import { BigNumber } from '@rotki/common';
import { type Theme, ThemeColors } from '@rotki/common/lib/settings';
import {
  type TimeFramePeriod,
  type TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { getBnFormat } from '@/data/amount_formatter';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { type CurrencyLocation } from '@/types/currency-location';
import { type DateFormat } from '@/types/date-format';
import {
  type BlockchainRefreshButtonBehaviour,
  type DashboardTablesVisibleColumns,
  type ExplorersSettings,
  FrontendSettings,
  type FrontendSettingsPayload,
  type ProfitLossTimeframe,
  type RefreshPeriod,
  type RoundingMode,
  SupportedLanguage
} from '@/types/frontend-settings';
import { type ActionStatus } from '@/types/action';
import {
  type BaseSuggestion,
  type SavedFilterLocation
} from '@/types/filtering';
import {
  CURRENT_DEFAULT_THEME_VERSION,
  DARK_COLORS,
  DEFAULT_THEME_HISTORIES,
  LIGHT_COLORS
} from '@/plugins/theme';

export const useFrontendSettingsStore = defineStore('settings/frontend', () => {
  const settings = reactive(FrontendSettings.parse({}));
  const defiSetupDone: ComputedRef<boolean> = computed(
    () => settings.defiSetupDone
  );
  const language: ComputedRef<SupportedLanguage> = computed(
    () => settings.language
  );
  const timeframeSetting: ComputedRef<TimeFrameSetting> = computed(
    () => settings.timeframeSetting
  );
  const visibleTimeframes: ComputedRef<TimeFrameSetting[]> = computed(
    () => settings.visibleTimeframes
  );
  const lastKnownTimeframe: ComputedRef<TimeFramePeriod> = computed(
    () => settings.lastKnownTimeframe
  );
  const queryPeriod: ComputedRef<number> = computed(() => settings.queryPeriod);
  const profitLossReportPeriod: ComputedRef<ProfitLossTimeframe> = computed(
    () => settings.profitLossReportPeriod
  );
  const thousandSeparator: ComputedRef<string> = computed(
    () => settings.thousandSeparator
  );
  const decimalSeparator: ComputedRef<string> = computed(
    () => settings.decimalSeparator
  );
  const currencyLocation: ComputedRef<CurrencyLocation> = computed(
    () => settings.currencyLocation
  );
  const abbreviateNumber: ComputedRef<boolean> = computed(
    () => settings.abbreviateNumber
  );
  const refreshPeriod: ComputedRef<RefreshPeriod> = computed(
    () => settings.refreshPeriod
  );
  const explorers: ComputedRef<ExplorersSettings> = computed(
    () => settings.explorers
  );
  const itemsPerPage: ComputedRef<number> = computed(
    () => settings.itemsPerPage
  );
  const amountRoundingMode: ComputedRef<RoundingMode> = computed(
    () => settings.amountRoundingMode
  );
  const valueRoundingMode: ComputedRef<RoundingMode> = computed(
    () => settings.valueRoundingMode
  );
  const selectedTheme: ComputedRef<Theme> = computed(
    () => settings.selectedTheme
  );
  const lightTheme: ComputedRef<ThemeColors> = computed(
    () => settings.lightTheme
  );
  const darkTheme: ComputedRef<ThemeColors> = computed(
    () => settings.darkTheme
  );
  const defaultThemeVersion: ComputedRef<number> = computed(
    () => settings.defaultThemeVersion
  );
  const graphZeroBased: ComputedRef<boolean> = computed(
    () => settings.graphZeroBased
  );
  const showGraphRangeSelector: ComputedRef<boolean> = computed(
    () => settings.showGraphRangeSelector
  );
  const nftsInNetValue: ComputedRef<boolean> = computed(
    () => settings.nftsInNetValue
  );
  const renderAllNftImages: ComputedRef<boolean> = computed(
    () => settings.renderAllNftImages
  );
  const whitelistedDomainsForNftImages: ComputedRef<string[]> = computed(
    () => settings.whitelistedDomainsForNftImages
  );
  const dashboardTablesVisibleColumns: ComputedRef<DashboardTablesVisibleColumns> =
    computed(() => settings.dashboardTablesVisibleColumns);
  const dateInputFormat: ComputedRef<DateFormat> = computed(
    () => settings.dateInputFormat
  );
  const versionUpdateCheckFrequency: ComputedRef<number> = computed(
    () => settings.versionUpdateCheckFrequency
  );
  const enableAliasNames: ComputedRef<boolean> = computed(
    () => settings.enableAliasNames
  );
  const blockchainRefreshButtonBehaviour: ComputedRef<BlockchainRefreshButtonBehaviour> =
    computed(() => settings.blockchainRefreshButtonBehaviour);

  const savedFilters: ComputedRef<{
    [key in SavedFilterLocation]?: BaseSuggestion[][];
  }> = computed(() => settings.savedFilters);

  const api = useSettingsApi();

  const update = (update: FrontendSettings): void => {
    Object.assign(settings, update);
    checkMachineLanguage();
  };

  async function updateSetting(
    payload: FrontendSettingsPayload
  ): Promise<ActionStatus> {
    const props = Object.keys(payload);
    assert(props.length > 0, 'Payload must be not-empty');
    try {
      const updatedSettings = { ...settings, ...payload };
      const { other } = await api.setSettings({
        frontendSettings: JSON.stringify(snakeCaseTransformer(updatedSettings))
      });

      update(updatedSettings);

      if (payload.thousandSeparator || payload.decimalSeparator) {
        BigNumber.config({
          FORMAT: getBnFormat(
            other.frontendSettings.thousandSeparator,
            other.frontendSettings.decimalSeparator
          )
        });
      }

      return {
        success: true
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  }

  const { lastLanguage, forceUpdateMachineLanguage } = useLastLanguage();

  const checkMachineLanguage = (): void => {
    if (get(forceUpdateMachineLanguage) === 'true') {
      set(lastLanguage, get(language));
    } else {
      set(lastLanguage, SupportedLanguage.EN);
    }
  };

  watch([language, forceUpdateMachineLanguage], () => {
    checkMachineLanguage();
  });

  const checkDefaultThemeVersion = () => {
    const defaultThemeVersionSetting = get(defaultThemeVersion);
    if (defaultThemeVersionSetting < CURRENT_DEFAULT_THEME_VERSION) {
      const historicDefaultTheme = DEFAULT_THEME_HISTORIES.find(
        ({ version }) => version === defaultThemeVersionSetting
      );

      if (historicDefaultTheme) {
        const newLightTheme: ThemeColors = { ...LIGHT_COLORS };
        const newDarkTheme: ThemeColors = { ...DARK_COLORS };
        const savedLightTheme = get(lightTheme);
        const savedDarkTheme = get(darkTheme);

        const accentColors = Object.keys(ThemeColors.shape);

        const isKeyOfThemeColors = (key: string): key is keyof ThemeColors =>
          accentColors.includes(key);

        accentColors.forEach(key => {
          if (!isKeyOfThemeColors(key)) {
            return;
          }

          // If saved theme isn't the same with the default theme at that version, do not replace with new default.
          if (historicDefaultTheme.lightColors[key] !== savedLightTheme[key]) {
            newLightTheme[key] = savedLightTheme[key];
          }

          if (historicDefaultTheme.darkColors[key] !== savedDarkTheme[key]) {
            newDarkTheme[key] = savedDarkTheme[key];
          }
        });

        startPromise(
          updateSetting({
            lightTheme: newLightTheme,
            darkTheme: newDarkTheme,
            defaultThemeVersion: CURRENT_DEFAULT_THEME_VERSION
          })
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
    savedFilters,
    // return settings on development for state persistence
    ...(checkIfDevelopment() ? { settings } : {}),
    updateSetting,
    update,
    checkDefaultThemeVersion
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useFrontendSettingsStore, import.meta.hot)
  );
}
