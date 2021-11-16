import { z } from 'zod';
import { currencies } from '@/data/currencies';
import { Currency } from '@/model/currency';
import { axiosCamelCaseTransformer } from '@/services/axios-tranformers';
import { defaultState } from '@/store/settings/state';
import { SettingsState } from '@/store/settings/types';
import { Writeable } from '@/types';
import { Exchange, KrakenAccountType } from '@/types/exchanges';
import { LedgerActionEnum } from '@/types/ledger-actions';
import { ModuleEnum } from '@/types/modules';

export const PriceOracle = z.enum(['cryptocompare', 'coingecko', 'manual']);
export type PriceOracle = z.infer<typeof PriceOracle>;

const OtherSettings = z.object({
  krakenAccountType: KrakenAccountType.optional(),
  frontendSettings: z.string().transform(arg => {
    const loadedSettings: Writeable<SettingsState> = defaultState();
    if (arg) {
      const fns = axiosCamelCaseTransformer(JSON.parse(arg));

      for (const [key, value] of Object.entries(loadedSettings)) {
        if (typeof fns[key] === typeof value) {
          // @ts-ignore
          loadedSettings[key] = fns[key];
        }
      }
    }

    return loadedSettings;
  }),
  premiumShouldSync: z.boolean(),
  havePremium: z.boolean()
});

type OtherSettings = z.infer<typeof OtherSettings>;

const GeneralSettings = z.object({
  uiFloatingPrecision: z.number(),
  submitUsageAnalytics: z.boolean(),
  ethRpcEndpoint: z.string(),
  ksmRpcEndpoint: z.string(),
  dotRpcEndpoint: z.string(),
  balanceSaveFrequency: z.number(),
  dateDisplayFormat: z.string(),
  mainCurrency: z.string().transform(currency => findCurrency(currency)),
  activeModules: z.array(ModuleEnum),
  btcDerivationGapLimit: z.number(),
  displayDateInLocaltime: z.boolean(),
  currentPriceOracles: z.array(PriceOracle),
  historicalPriceOracles: z.array(PriceOracle),
  ssf0graphMultiplier: z.number()
});

export type GeneralSettings = z.infer<typeof GeneralSettings>;

const AccountingSettings = z.object({
  calculatePastCostBasis: z.boolean(),
  pnlCsvWithFormulas: z.boolean(),
  pnlCsvHaveSummary: z.boolean(),
  includeCrypto2crypto: z.boolean(),
  includeGasCosts: z.boolean(),
  taxfreeAfterPeriod: z.number().nullable(),
  accountForAssetsMovements: z.boolean(),
  taxableLedgerActions: z.array(LedgerActionEnum)
});

export type AccountingSettings = z.infer<typeof AccountingSettings>;

export type AccountingSettingsUpdate = Partial<AccountingSettings>;

const findCurrency = (currencySymbol: string) => {
  const currency: Currency | undefined = currencies.find(
    currency => currency.ticker_symbol === currencySymbol
  );
  if (!currency) {
    throw new Error(`Could not find ${currencySymbol}`);
  }
  return currency;
};

const Settings = GeneralSettings.merge(AccountingSettings).merge(OtherSettings);

const SettingsUpdate = Settings.merge(
  z.object({
    mainCurrency: z.string(),
    frontendSettings: z.string()
  })
);

export type SettingsUpdate = Partial<z.infer<typeof SettingsUpdate>>;

const BaseData = z.object({
  version: z.number(),
  lastWriteTs: z.number(),
  lastDataUploadTs: z.number(),
  lastBalanceSave: z.number()
});

type BaseData = z.infer<typeof BaseData>;

export const UserSettings = BaseData.merge(Settings);

type UserSettings = z.infer<typeof UserSettings>;

const getAccountingSettings = (settings: UserSettings): AccountingSettings => ({
  taxfreeAfterPeriod: settings.taxfreeAfterPeriod,
  pnlCsvWithFormulas: settings.pnlCsvWithFormulas,
  pnlCsvHaveSummary: settings.pnlCsvHaveSummary,
  includeGasCosts: settings.includeGasCosts,
  includeCrypto2crypto: settings.includeCrypto2crypto,
  accountForAssetsMovements: settings.accountForAssetsMovements,
  calculatePastCostBasis: settings.calculatePastCostBasis,
  taxableLedgerActions: settings.taxableLedgerActions
});

const getGeneralSettings = (settings: UserSettings): GeneralSettings => ({
  uiFloatingPrecision: settings.uiFloatingPrecision,
  mainCurrency: settings.mainCurrency,
  dateDisplayFormat: settings.dateDisplayFormat,
  balanceSaveFrequency: settings.balanceSaveFrequency,
  ethRpcEndpoint: settings.ethRpcEndpoint,
  ksmRpcEndpoint: settings.ksmRpcEndpoint,
  dotRpcEndpoint: settings.dotRpcEndpoint,
  submitUsageAnalytics: settings.submitUsageAnalytics,
  activeModules: settings.activeModules,
  btcDerivationGapLimit: settings.btcDerivationGapLimit,
  displayDateInLocaltime: settings.displayDateInLocaltime,
  currentPriceOracles: settings.currentPriceOracles,
  historicalPriceOracles: settings.historicalPriceOracles,
  ssf0graphMultiplier: settings.ssf0graphMultiplier
});

const getOtherSettings = (settings: UserSettings): OtherSettings => ({
  krakenAccountType: settings.krakenAccountType,
  frontendSettings: settings.frontendSettings,
  premiumShouldSync: settings.premiumShouldSync,
  havePremium: settings.havePremium
});

const getData = (settings: UserSettings): BaseData => ({
  lastDataUploadTs: settings.lastDataUploadTs,
  lastBalanceSave: settings.lastBalanceSave,
  version: settings.version,
  lastWriteTs: settings.lastWriteTs
});

export const UserSettingsModel = UserSettings.transform(settings => ({
  general: getGeneralSettings(settings),
  accounting: getAccountingSettings(settings),
  other: getOtherSettings(settings),
  data: getData(settings)
}));

export type UserSettingsModel = z.infer<typeof UserSettingsModel>;

export const UserAccount = z.object({
  settings: UserSettingsModel,
  exchanges: z.array(Exchange)
});

export type UserAccount = z.infer<typeof UserAccount>;
