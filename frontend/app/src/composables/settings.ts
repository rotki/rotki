import { computed, ref, watch } from '@vue/composition-api';
import { promiseTimeout, set, useTimeoutFn } from '@vueuse/core';
import { BaseMessage } from '@/components/settings/utils';
import i18n from '@/i18n';
import { ActionStatus } from '@/store/types';
import { useStore } from '@/store/utils';
import { DateFormat } from '@/types/date-format';
import {
  DashboardTablesVisibleColumns,
  ExplorersSettings,
  FrontendSettingsPayload,
  RoundingMode
} from '@/types/frontend-settings';
import { AccountingSettings, SettingsUpdate } from '@/types/user';
import { assert } from '@/utils/assertions';
import { logger } from '@/utils/logging';

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

  const showGraphRangeSelector = computed<boolean>(
    () => store.state.settings!.showGraphRangeSelector
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
    showGraphRangeSelector,
    nftsInNetValue,
    updateSetting
  };
};

export const useSettings = () => {
  const store = useStore();

  const accountingSettings = computed<AccountingSettings>(() => {
    return store.state!.session!.accountingSettings;
  });

  const updateSetting = async (
    settings: SettingsUpdate,
    messages: BaseMessage
  ) => {
    const updateKeys = Object.keys(settings);
    assert(
      updateKeys.length === 1,
      'Settings update should only contain a single setting'
    );

    let message: { success: string } | { error: string } = {
      error: messages.error
    };
    try {
      const { success } = (await store.dispatch(
        'session/settingsUpdate',
        settings
      )) as ActionStatus;

      if (success) {
        message = {
          success: messages.success
        };
      }
    } catch (e) {
      logger.error(e);
    }

    return message;
  };

  return {
    accountingSettings,
    updateSetting
  };
};

export const useClearableMessages = () => {
  const error = ref('');
  const success = ref('');

  const clear = () => {
    set(error, '');
    set(success, '');
  };

  const formatMessage = (base: string, extra?: string) => {
    if (extra) {
      return `${base}: ${extra}`;
    }
    return base;
  };

  const setSuccess = (message: string) => {
    set(success, formatMessage(i18n.tc('settings.saved'), message));
  };

  const setError = (message: string) => {
    set(error, formatMessage(i18n.tc('settings.not_saved'), message));
  };

  const wait = async () => await promiseTimeout(200);
  const { start, stop } = useTimeoutFn(clear, 5500);
  watch([error, success], ([error, success]) => {
    if (error || success) {
      start();
    }
  });

  return {
    error,
    success,
    setSuccess,
    setError,
    wait,
    stop,
    clear
  };
};
