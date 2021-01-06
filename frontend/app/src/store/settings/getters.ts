import { TAX_REPORT_PERIOD } from '@/store/settings/consts';
import { SettingsState, TaxReportPeriod } from '@/store/settings/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';

type SettingsGetters = {
  [TAX_REPORT_PERIOD]: TaxReportPeriod;
};

export const getters: Getters<
  SettingsState,
  SettingsGetters,
  RotkehlchenState,
  any
> = {
  [TAX_REPORT_PERIOD]: state => state[TAX_REPORT_PERIOD]
};
