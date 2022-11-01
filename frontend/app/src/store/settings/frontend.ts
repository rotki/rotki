import { BigNumber } from '@rotki/common';
import { Theme, ThemeColors } from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { ComputedRef } from 'vue';
import { useLastLanguage } from '@/composables/session/language';
import { getBnFormat } from '@/data/amount_formatter';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { useSettingsApi } from '@/services/settings/settings-api';
import { ActionStatus } from '@/store/types';
import { CurrencyLocation } from '@/types/currency-location';
import { DateFormat } from '@/types/date-format';
import {
  DashboardTablesVisibleColumns,
  ExplorersSettings,
  FrontendSettings,
  FrontendSettingsPayload,
  ProfitLossTimeframe,
  RefreshPeriod,
  RoundingMode,
  SupportedLanguage
} from '@/types/frontend-settings';
import { assert } from '@/utils/assertions';

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
  const graphZeroBased: ComputedRef<boolean> = computed(
    () => settings.graphZeroBased
  );
  const showGraphRangeSelector: ComputedRef<boolean> = computed(
    () => settings.showGraphRangeSelector
  );
  const nftsInNetValue: ComputedRef<boolean> = computed(
    () => settings.nftsInNetValue
  );
  const dashboardTablesVisibleColumns: ComputedRef<DashboardTablesVisibleColumns> =
    computed(() => settings.dashboardTablesVisibleColumns);
  const dateInputFormat: ComputedRef<DateFormat> = computed(
    () => settings.dateInputFormat
  );
  const versionUpdateCheckFrequency: ComputedRef<number> = computed(
    () => settings.versionUpdateCheckFrequency
  );
  const enableEthNames: ComputedRef<boolean> = computed(
    () => settings.enableEthNames
  );

  const api = useSettingsApi();

  const update = (update: FrontendSettings) => {
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
        frontendSettings: JSON.stringify(
          axiosSnakeCaseTransformer(updatedSettings)
        )
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

  const checkMachineLanguage = () => {
    if (get(forceUpdateMachineLanguage) === 'true') {
      set(lastLanguage, get(language));
    } else {
      set(lastLanguage, SupportedLanguage.EN);
    }
  };

  watch([language, forceUpdateMachineLanguage], () => {
    checkMachineLanguage();
  });

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
    dashboardTablesVisibleColumns,
    dateInputFormat,
    versionUpdateCheckFrequency,
    enableEthNames,
    updateSetting,
    update
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useFrontendSettingsStore, import.meta.hot)
  );
}
