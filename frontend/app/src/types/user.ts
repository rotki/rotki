import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { Constraints } from '@/data/constraints';
import { AddressNamePriorityEnum } from '@/types/settings/address-name-priorities';
import { useCurrencies } from '@/types/currencies';
import { Exchange, KrakenAccountType } from '@/types/exchanges';
import { FrontendSettings } from '@/types/settings/frontend-settings';
import { ModuleEnum } from '@/types/modules';
import { PriceOracleEnum } from '@/types/settings/price-oracle';
import { type ToSnakeCase } from '@/types/common';
import { camelCaseTransformer } from '@/services/axios-tranformers';

export const OtherSettings = z.object({
  krakenAccountType: KrakenAccountType.optional(),
  frontendSettings: z.string().transform(arg => {
    const data = arg ? camelCaseTransformer(JSON.parse(arg)) : {};
    return FrontendSettings.parse(data);
  }),
  premiumShouldSync: z.boolean(),
  havePremium: z.boolean()
});

export type OtherSettings = z.infer<typeof OtherSettings>;

const GeneralSettings = z.object({
  uiFloatingPrecision: z.number(),
  submitUsageAnalytics: z.boolean(),
  ksmRpcEndpoint: z.string(),
  dotRpcEndpoint: z.string(),
  balanceSaveFrequency: z.preprocess(
    balanceSaveFrequency =>
      Math.min(
        Number.parseInt(balanceSaveFrequency as string),
        Constraints.MAX_HOURS_DELAY
      ),
    z.number().int().max(Constraints.MAX_HOURS_DELAY)
  ),
  dateDisplayFormat: z.string(),
  mainCurrency: z.string().transform(currency => {
    const { findCurrency } = useCurrencies();
    return findCurrency(currency);
  }),
  activeModules: z.array(ModuleEnum),
  btcDerivationGapLimit: z.number(),
  displayDateInLocaltime: z.boolean(),
  currentPriceOracles: z.array(PriceOracleEnum),
  historicalPriceOracles: z.array(PriceOracleEnum),
  ssfGraphMultiplier: z.number().default(0),
  inferZeroTimedBalances: z.boolean(),
  nonSyncingExchanges: z.array(Exchange),
  treatEth2AsEth: z.boolean(),
  addressNamePriority: z.array(AddressNamePriorityEnum),
  queryRetryLimit: z.number().min(1),
  connectTimeout: z.number().min(1),
  readTimeout: z.number().min(1)
});

export type GeneralSettings = z.infer<typeof GeneralSettings>;

export enum CostBasisMethod {
  FIFO = 'fifo',
  LIFO = 'lifo',
  HIFO = 'hifo',
  ACB = 'acb'
}

export const CostBasisMethodEnum = z.nativeEnum(CostBasisMethod);

export const BaseAccountingSettings = z.object({
  calculatePastCostBasis: z.boolean(),
  includeCrypto2crypto: z.boolean(),
  includeGasCosts: z.boolean(),
  taxfreeAfterPeriod: z.number().nullish(),
  accountForAssetsMovements: z.boolean(),
  profitCurrency: z.string().nullish(),
  ethStakingTaxableAfterWithdrawalEnabled: z.boolean().nullish(),
  costBasisMethod: CostBasisMethodEnum.nullish()
});

export type BaseAccountingSettings = z.infer<typeof BaseAccountingSettings>;

const AccountingSettings = z
  .object({
    pnlCsvWithFormulas: z.boolean(),
    pnlCsvHaveSummary: z.boolean(),
    costBasisMethod: CostBasisMethodEnum.default(CostBasisMethod.FIFO)
  })
  .merge(BaseAccountingSettings);

export type AccountingSettings = z.infer<typeof AccountingSettings>;

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
  costBasisMethod: settings.costBasisMethod,
  ethStakingTaxableAfterWithdrawalEnabled:
    settings.ethStakingTaxableAfterWithdrawalEnabled
});

const getGeneralSettings = (settings: UserSettings): GeneralSettings => ({
  uiFloatingPrecision: settings.uiFloatingPrecision,
  mainCurrency: settings.mainCurrency,
  dateDisplayFormat: settings.dateDisplayFormat,
  balanceSaveFrequency: settings.balanceSaveFrequency,
  ksmRpcEndpoint: settings.ksmRpcEndpoint,
  dotRpcEndpoint: settings.dotRpcEndpoint,
  submitUsageAnalytics: settings.submitUsageAnalytics,
  activeModules: settings.activeModules,
  btcDerivationGapLimit: settings.btcDerivationGapLimit,
  displayDateInLocaltime: settings.displayDateInLocaltime,
  currentPriceOracles: settings.currentPriceOracles,
  historicalPriceOracles: settings.historicalPriceOracles,
  ssfGraphMultiplier: settings.ssfGraphMultiplier,
  inferZeroTimedBalances: settings.inferZeroTimedBalances,
  nonSyncingExchanges: settings.nonSyncingExchanges,
  treatEth2AsEth: settings.treatEth2AsEth,
  addressNamePriority: settings.addressNamePriority,
  queryRetryLimit: settings.queryRetryLimit,
  connectTimeout: settings.connectTimeout,
  readTimeout: settings.readTimeout
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

const ApiKey = z.object({
  apiKey: z.string()
});

export const ExternalServiceKeys = z.object({
  etherscan: z.record(ApiKey.optional()).optional(),
  cryptocompare: ApiKey.optional(),
  covalent: ApiKey.optional(),
  beaconchain: ApiKey.optional(),
  loopring: ApiKey.optional(),
  opensea: ApiKey.optional()
});

export type ExternalServiceKeys = z.infer<typeof ExternalServiceKeys>;

export type ExternalServiceName = ToSnakeCase<keyof ExternalServiceKeys>;

export interface ExternalServiceKey {
  readonly name: string;
  readonly apiKey: string;
}

export const ExchangeRates = z.record(NumericString);

export type ExchangeRates = z.infer<typeof ExchangeRates>;
