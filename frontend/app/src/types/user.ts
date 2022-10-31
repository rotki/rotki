import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { Constraints } from '@/data/constraints';
import { axiosCamelCaseTransformer } from '@/services/axios-tranformers';
import { useCurrencies } from '@/types/currencies';
import { Exchange, KrakenAccountType } from '@/types/exchanges';
import { FrontendSettings } from '@/types/frontend-settings';
import { LedgerActionEnum } from '@/types/ledger-actions';
import { ModuleEnum } from '@/types/modules';
import { PriceOracleEnum } from '@/types/price-oracle';

const OtherSettings = z.object({
  krakenAccountType: KrakenAccountType.optional(),
  frontendSettings: z.string().transform(arg => {
    const data = arg ? axiosCamelCaseTransformer(JSON.parse(arg)) : {};
    return FrontendSettings.parse(data);
  }),
  premiumShouldSync: z.boolean(),
  havePremium: z.boolean()
});

type OtherSettings = z.infer<typeof OtherSettings>;

const GeneralSettings = z.object({
  uiFloatingPrecision: z.number(),
  submitUsageAnalytics: z.boolean(),
  ksmRpcEndpoint: z.string(),
  dotRpcEndpoint: z.string(),
  balanceSaveFrequency: z.preprocess(
    balanceSaveFrequency =>
      Math.min(
        parseInt(balanceSaveFrequency as string),
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
  ssf0graphMultiplier: z.number().default(0),
  nonSyncingExchanges: z.array(Exchange),
  treatEth2AsEth: z.boolean()
});

export type GeneralSettings = z.infer<typeof GeneralSettings>;

export enum CostBasisMethod {
  Fifo = 'fifo',
  Lifo = 'lifo'
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
    taxableLedgerActions: z.array(LedgerActionEnum),
    costBasisMethod: CostBasisMethodEnum.default(CostBasisMethod.Fifo)
  })
  .merge(BaseAccountingSettings);

export type AccountingSettings = z.infer<typeof AccountingSettings>;

export type AccountingSettingsUpdate = Partial<AccountingSettings>;

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
  taxableLedgerActions: settings.taxableLedgerActions,
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
  ssf0graphMultiplier: settings.ssf0graphMultiplier,
  nonSyncingExchanges: settings.nonSyncingExchanges,
  treatEth2AsEth: settings.treatEth2AsEth
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
  etherscan: ApiKey.optional(),
  cryptocompare: ApiKey.optional(),
  covalent: ApiKey.optional(),
  beaconchain: ApiKey.optional(),
  loopring: ApiKey.optional(),
  opensea: ApiKey.optional()
});

export type ExternalServiceKeys = z.infer<typeof ExternalServiceKeys>;
export type ExternalServiceName = keyof ExternalServiceKeys;

export interface ExternalServiceKey {
  readonly name: ExternalServiceName;
  readonly apiKey: string;
}

export const Tag = z.object({
  name: z.string(),
  description: z.string(),
  backgroundColor: z.string(),
  foregroundColor: z.string(),
  readOnly: z.boolean().default(false).optional(),
  icon: z.string().default('').optional()
});

export type Tag = z.infer<typeof Tag>;

export enum ReadOnlyTag {
  LOOPRING = 'Loopring'
}

export const READ_ONLY_TAGS: Record<ReadOnlyTag, Tag> = {
  [ReadOnlyTag.LOOPRING]: {
    name: ReadOnlyTag.LOOPRING,
    description: ReadOnlyTag.LOOPRING,
    backgroundColor: 'C5DEF5',
    foregroundColor: '000000',
    readOnly: true,
    icon: '/assets/images/modules/loopring.svg'
  }
};

export const Tags = z.record(Tag);

export type Tags = z.infer<typeof Tags>;

export const ExchangeRates = z.record(NumericString);

export type ExchangeRates = z.infer<typeof ExchangeRates>;
