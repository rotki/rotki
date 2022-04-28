import { BigNumber } from '@rotki/common';
import { computed } from '@vue/composition-api';
import { useStore } from '@/store/utils';
import { DateFormat } from '@/types/date-format';
import {
  DashboardTablesVisibleColumns,
  ExplorersSettings,
  FrontendSettingsPayload
} from '@/types/frontend-settings';
import RoundingMode = BigNumber.RoundingMode;

export const setupSettings = () => {
  const store = useStore();

  const dashboardTablesVisibleColumns = computed<DashboardTablesVisibleColumns>(
    () => store.getters['settings/dashboardTablesVisibleColumns']
  );

  const dateInputFormat = computed<DateFormat>(
    () => store.getters['settings/dateInputFormat']
  );

  const itemsPerPage = computed<number>(
    () => store.state.settings!.itemsPerPage
  );

  const refreshPeriod = computed<number>(
    () => store.state.settings!.refreshPeriod
  );

  const thousandSeparator = computed<string>(
    () => store.getters['settings/thousandSeparator']
  );

  const decimalSeparator = computed<string>(
    () => store.getters['settings/decimalSeparator']
  );

  const currencyLocation = computed<string>(
    () => store.getters['settings/currencyLocation']
  );

  const amountRoundingMode = computed<RoundingMode>(
    () => store.state.settings!.amountRoundingMode
  );

  const valueRoundingMode = computed<RoundingMode>(
    () => store.state.settings!.valueRoundingMode
  );

  const graphZeroBased = computed<boolean>(
    () => store.state.settings!.graphZeroBased
  );

  const nftsInNetValue = computed<boolean>(
    () => store.state.settings!.nftsInNetValue
  );

  const explorers = computed<ExplorersSettings>(
    () => store.state.settings!.explorers
  );

  const updateSetting = async (
    settings: FrontendSettingsPayload
  ): Promise<void> => {
    await store.dispatch('settings/updateSetting', settings);
  };

  return {
    dateInputFormat,
    dashboardTablesVisibleColumns,
    itemsPerPage,
    refreshPeriod,
    thousandSeparator,
    decimalSeparator,
    currencyLocation,
    amountRoundingMode,
    valueRoundingMode,
    explorers,
    graphZeroBased,
    nftsInNetValue,
    updateSetting
  };
};
