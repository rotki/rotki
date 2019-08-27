import { currencies } from '@/data/currencies';
import { defaultAccountingSettings, defaultSettings } from '@/data/factories';
import { Currency } from '@/model/currency';
import { AccountingSettings, GeneralSettings } from '@/typing/types';

export interface SessionState {
  newUser: boolean;
  currency: Currency;
  logged: boolean;
  settings: GeneralSettings;
  accountingSettings: AccountingSettings;
  premium: boolean;
  premiumSync: boolean;
  nodeConnection: boolean;
}

export const createSessionState: () => SessionState = () => ({
  newUser: false,
  currency: currencies[0],
  logged: false,
  settings: defaultSettings(),
  accountingSettings: defaultAccountingSettings(),
  premium: false,
  premiumSync: false,
  nodeConnection: false
});

export const state: SessionState = createSessionState();
