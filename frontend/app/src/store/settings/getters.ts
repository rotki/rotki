import {
  CURRENCY_LOCATION,
  DARK_MODE_ENABLED,
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
  [DARK_MODE_ENABLED]: boolean;
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
  [CURRENCY_LOCATION]: state => state[CURRENCY_LOCATION],
  [DARK_MODE_ENABLED]: state => state[DARK_MODE_ENABLED]
};
