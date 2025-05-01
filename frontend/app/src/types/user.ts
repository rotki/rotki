import type { ToSnakeCase } from '@/types/common';
import { Constraints } from '@/data/constraints';
import { useCurrencies } from '@/types/currencies';
import { Exchange, KrakenAccountType } from '@/types/exchanges';
import { ModuleEnum } from '@/types/modules';
import { AddressNamePriorityEnum } from '@/types/settings/address-name-priorities';
import { parseFrontendSettings } from '@/types/settings/frontend-settings';
import { PriceOracleEnum } from '@/types/settings/price-oracle';
import { NumericString } from '@rotki/common';
import { z } from 'zod';

export const OtherSettings = z.object({
  frontendSettings: z.string().transform(parseFrontendSettings),
  havePremium: z.boolean(),
  krakenAccountType: KrakenAccountType.optional(),
  premiumShouldSync: z.boolean(),
});

export type OtherSettings = z.infer<typeof OtherSettings>;

const GeneralSettings = z.object({
  activeModules: z.array(ModuleEnum),
  addressNamePriority: z.array(AddressNamePriorityEnum),
  askUserUponSizeDiscrepancy: z.boolean(),
  autoCreateCalendarReminders: z.boolean(),
  autoDeleteCalendarEntries: z.boolean(),
  autoDetectTokens: z.boolean(),
  balanceSaveFrequency: z.preprocess(
    balanceSaveFrequency => Math.min(Number.parseInt(balanceSaveFrequency as string), Constraints.MAX_HOURS_DELAY),
    z.number().int().max(Constraints.MAX_HOURS_DELAY),
  ),
  beaconRpcEndpoint: z.string(),
  btcDerivationGapLimit: z.number(),
  connectTimeout: z.number().min(1),
  csvExportDelimiter: z.string().max(1),
  currentPriceOracles: z.array(PriceOracleEnum),
  dateDisplayFormat: z.string(),
  displayDateInLocaltime: z.boolean(),
  dotRpcEndpoint: z.string(),
  evmchainsToSkipDetection: z.array(z.string()),
  historicalPriceOracles: z.array(PriceOracleEnum),
  inferZeroTimedBalances: z.boolean(),
  ksmRpcEndpoint: z.string(),
  mainCurrency: z.string().transform((currency) => {
    const { findCurrency } = useCurrencies();
    return findCurrency(currency);
  }),
  nonSyncingExchanges: z.array(Exchange),
  oraclePenaltyDuration: z.number().min(1),
  oraclePenaltyThresholdCount: z.number().min(1),
  queryRetryLimit: z.number().min(1),
  readTimeout: z.number().min(1),
  ssfGraphMultiplier: z.number().default(0),
  submitUsageAnalytics: z.boolean(),
  treatEth2AsEth: z.boolean(),
  uiFloatingPrecision: z.number(),
});

export type GeneralSettings = z.infer<typeof GeneralSettings>;

export enum CostBasisMethod {
  FIFO = 'fifo',
  LIFO = 'lifo',
  HIFO = 'hifo',
  ACB = 'acb',
}

export const CostBasisMethodEnum = z.nativeEnum(CostBasisMethod);

export const BaseAccountingSettings = z.object({
  calculatePastCostBasis: z.boolean(),
  costBasisMethod: CostBasisMethodEnum.nullish(),
  ethStakingTaxableAfterWithdrawalEnabled: z.boolean().nullish(),
  includeCrypto2crypto: z.boolean(),
  includeFeesInCostBasis: z.boolean().nullish(),
  includeGasCosts: z.boolean(),
  profitCurrency: z.string().nullish(),
  taxfreeAfterPeriod: z.number().nullish(),
});

export type BaseAccountingSettings = z.infer<typeof BaseAccountingSettings>;

const AccountingSettings = z
  .object({
    costBasisMethod: CostBasisMethodEnum.default(CostBasisMethod.FIFO),
    pnlCsvHaveSummary: z.boolean(),
    pnlCsvWithFormulas: z.boolean(),
  })
  .merge(BaseAccountingSettings);

export type AccountingSettings = z.infer<typeof AccountingSettings>;

const Settings = GeneralSettings.merge(AccountingSettings).merge(OtherSettings);

const SettingsUpdate = Settings.merge(
  z.object({
    frontendSettings: z.string(),
    mainCurrency: z.string(),
  }),
);

export type SettingsUpdate = Partial<z.infer<typeof SettingsUpdate>>;

const BaseData = z.object({
  lastBalanceSave: z.number(),
  lastDataUploadTs: z.number(),
  lastWriteTs: z.number(),
  version: z.number(),
});

type BaseData = z.infer<typeof BaseData>;

export const UserSettings = BaseData.merge(Settings);

type UserSettings = z.infer<typeof UserSettings>;

function getAccountingSettings(settings: UserSettings): AccountingSettings {
  return {
    calculatePastCostBasis: settings.calculatePastCostBasis,
    costBasisMethod: settings.costBasisMethod,
    ethStakingTaxableAfterWithdrawalEnabled: settings.ethStakingTaxableAfterWithdrawalEnabled,
    includeCrypto2crypto: settings.includeCrypto2crypto,
    includeFeesInCostBasis: settings.includeFeesInCostBasis,
    includeGasCosts: settings.includeGasCosts,
    pnlCsvHaveSummary: settings.pnlCsvHaveSummary,
    pnlCsvWithFormulas: settings.pnlCsvWithFormulas,
    taxfreeAfterPeriod: settings.taxfreeAfterPeriod,
  };
}

function getGeneralSettings(settings: UserSettings): GeneralSettings {
  return {
    activeModules: settings.activeModules,
    addressNamePriority: settings.addressNamePriority,
    askUserUponSizeDiscrepancy: settings.askUserUponSizeDiscrepancy,
    autoCreateCalendarReminders: settings.autoCreateCalendarReminders,
    autoDeleteCalendarEntries: settings.autoDeleteCalendarEntries,
    autoDetectTokens: settings.autoDetectTokens,
    balanceSaveFrequency: settings.balanceSaveFrequency,
    beaconRpcEndpoint: settings.beaconRpcEndpoint,
    btcDerivationGapLimit: settings.btcDerivationGapLimit,
    connectTimeout: settings.connectTimeout,
    csvExportDelimiter: settings.csvExportDelimiter,
    currentPriceOracles: settings.currentPriceOracles,
    dateDisplayFormat: settings.dateDisplayFormat,
    displayDateInLocaltime: settings.displayDateInLocaltime,
    dotRpcEndpoint: settings.dotRpcEndpoint,
    evmchainsToSkipDetection: settings.evmchainsToSkipDetection,
    historicalPriceOracles: settings.historicalPriceOracles,
    inferZeroTimedBalances: settings.inferZeroTimedBalances,
    ksmRpcEndpoint: settings.ksmRpcEndpoint,
    mainCurrency: settings.mainCurrency,
    nonSyncingExchanges: settings.nonSyncingExchanges,
    oraclePenaltyDuration: settings.oraclePenaltyDuration,
    oraclePenaltyThresholdCount: settings.oraclePenaltyThresholdCount,
    queryRetryLimit: settings.queryRetryLimit,
    readTimeout: settings.readTimeout,
    ssfGraphMultiplier: settings.ssfGraphMultiplier,
    submitUsageAnalytics: settings.submitUsageAnalytics,
    treatEth2AsEth: settings.treatEth2AsEth,
    uiFloatingPrecision: settings.uiFloatingPrecision,
  };
}

function getOtherSettings(settings: UserSettings): OtherSettings {
  return {
    frontendSettings: settings.frontendSettings,
    havePremium: settings.havePremium,
    krakenAccountType: settings.krakenAccountType,
    premiumShouldSync: settings.premiumShouldSync,
  };
}

function getData(settings: UserSettings): BaseData {
  return {
    lastBalanceSave: settings.lastBalanceSave,
    lastDataUploadTs: settings.lastDataUploadTs,
    lastWriteTs: settings.lastWriteTs,
    version: settings.version,
  };
}

export const UserSettingsModel = UserSettings.transform(settings => ({
  accounting: getAccountingSettings(settings),
  data: getData(settings),
  general: getGeneralSettings(settings),
  other: getOtherSettings(settings),
}));

export type UserSettingsModel = z.infer<typeof UserSettingsModel>;

export const UserAccount = z.object({
  exchanges: z.array(Exchange),
  settings: UserSettingsModel,
});

export type UserAccount = z.infer<typeof UserAccount>;

const ApiKey = z.object({
  apiKey: z.string(),
});

const Auth = z.object({
  password: z.string(),
  username: z.string(),
});

export type Auth = z.infer<typeof Auth>;

export const ExternalServiceKeys = z.object({
  alchemy: ApiKey.optional(),
  beaconchain: ApiKey.optional(),
  blockscout: z.record(ApiKey.nullable()).optional(),
  coingecko: ApiKey.optional(),
  covalent: ApiKey.optional(),
  cryptocompare: ApiKey.optional(),
  defillama: ApiKey.optional(),
  etherscan: ApiKey.optional(),
  gnosis_pay: ApiKey.optional(),
  loopring: ApiKey.optional(),
  monerium: Auth.optional(),
  opensea: ApiKey.optional(),
  thegraph: ApiKey.optional(),
});

export type ExternalServiceKeys = z.infer<typeof ExternalServiceKeys>;

export type ExternalServiceName = ToSnakeCase<keyof ExternalServiceKeys>;

export interface ExternalServicePayloadWithApiKey {
  readonly name: string;
  readonly apiKey: string;
}

export interface ExternalServicePayloadWithAuth {
  readonly name: string;
  readonly username: string;
  readonly password: string;
}

export type ExternalServiceKey = ExternalServicePayloadWithApiKey | ExternalServicePayloadWithAuth;

export const ExchangeRates = z.record(NumericString);

export type ExchangeRates = z.infer<typeof ExchangeRates>;
