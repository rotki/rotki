import { currencies } from '@/data/currencies';
import { defaultAccountingSettings, defaultSettings } from '@/data/factories';
import { Currency } from '@/model/currency';
import { AccountingSettings, GeneralSettings } from '@/typing/types';

export interface SessionState {
  newUser: boolean;
  logged: boolean;
  username: string;
  currency: Currency;
  settings: GeneralSettings;
  accountingSettings: AccountingSettings;
  premium: boolean;
  premiumSync: boolean;
  nodeConnection: boolean;
}

export const defaultState: () => SessionState = () => ({
  newUser: false,
  logged: false,
  username: '',
  currency: currencies[0],
  settings: defaultSettings(),
  accountingSettings: defaultAccountingSettings(),
  premium: false,
  premiumSync: false,
  nodeConnection: false
});

export const state: SessionState = defaultState();
