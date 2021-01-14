import {
  CURRENCY_LOCATION,
  DECIMAL_SEPARATOR,
  PROFIT_LOSS_PERIOD,
  THOUSAND_SEPARATOR
} from '@/store/settings/consts';
import { SettingsState, ProfitLossTimeframe } from '@/store/settings/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { CurrencyLocation } from '@/typing/types';

type SettingsGetters = {
  [PROFIT_LOSS_PERIOD]: ProfitLossTimeframe;
  [THOUSAND_SEPARATOR]: string;
  [DECIMAL_SEPARATOR]: string;
  [CURRENCY_LOCATION]: CurrencyLocation;
};

export const getters: Getters<
  SettingsState,
  SettingsGetters,
  RotkehlchenState,
  any
> = {
  [PROFIT_LOSS_PERIOD]: state => state[PROFIT_LOSS_PERIOD],
  [THOUSAND_SEPARATOR]: state => state[THOUSAND_SEPARATOR],
  [DECIMAL_SEPARATOR]: state => state[DECIMAL_SEPARATOR],
  [CURRENCY_LOCATION]: state => state[CURRENCY_LOCATION]
};
