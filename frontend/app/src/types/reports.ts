import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { Entries } from '@/types/common';
import { Quarter } from '@/types/frontend-settings';
import { BaseAccountingSettings } from '@/types/user';

export enum ProfitLossEventTypeEnum {
  TRADE = 'trade',
  FEE = 'fee',
  ASSET_MOVEMENT = 'asset movement',
  MARGIN_POSITION = 'margin position',
  LOAN = 'loan',
  PREFORK_ACQUISITION = 'prefork acquisition',
  LEDGER_ACTION = 'ledger action',
  STAKING = 'staking',
  HISTORY_BASE_ENTRY = 'history base entry',
  TRANSACTION_EVENT = 'transaction event'
}

export const ProfitLossOverviewItem = z.object({
  taxable: NumericString,
  free: NumericString
});

export type ProfitLossOverviewItem = z.infer<typeof ProfitLossOverviewItem>;

export const ProfitLossOverview = z.record(ProfitLossOverviewItem);

export type ProfitLossOverview = z.infer<typeof ProfitLossOverview>;

export const MatchedAcquisitionsEvent = z.object({
  fullAmount: NumericString,
  index: z.number(),
  rate: NumericString,
  timestamp: z.number()
});

export const MatchedAcquisitions = z.object({
  amount: NumericString.nullish(),
  taxable: z.boolean(),
  event: MatchedAcquisitionsEvent
});

export const CostBasis = z.object({
  isComplete: z.boolean().nullish(),
  matchedAcquisitions: z.array(MatchedAcquisitions).nullish()
});

export type CostBasis = z.infer<typeof CostBasis>;

export const ProfitLossEvent = z.object({
  asset: z.string(),
  costBasis: CostBasis.nullable(),
  freeAmount: NumericString,
  location: z.string(),
  notes: z.string(),
  pnlFree: NumericString,
  pnlTaxable: NumericString,
  price: NumericString,
  taxableAmount: NumericString,
  timestamp: z.number(),
  type: z.string(),
  groupId: z.string().nullish()
});

export type ProfitLossEvent = z.infer<typeof ProfitLossEvent>;

export const Report = z.object({
  identifier: z.number(),
  firstProcessedTimestamp: z.number(),
  lastProcessedTimestamp: z.number(),
  processedActions: z.number(),
  totalActions: z.number(),
  startTs: z.number(),
  endTs: z.number(),
  sizeOnDisk: z.number(),
  timestamp: z.number(),
  settings: BaseAccountingSettings,
  overview: ProfitLossOverview
});

export type Report = z.infer<typeof Report>;

const ProfitLossEvents = z.array(ProfitLossEvent);

export type ProfitLossEvents = z.infer<typeof ProfitLossEvents>;

export const ReportProgress = z.object({
  processingState: z.string(),
  totalProgress: z.string()
});

export type ReportProgress = z.infer<typeof ReportProgress>;

export type ReportError = {
  error: string;
  message: string;
};

export const Reports = Entries(z.array(Report));

export type Reports = z.infer<typeof Reports>;

export const ProfitLossReportOverview = Entries(z.array(ProfitLossOverview));

export type ProfitLossReportOverview = z.infer<typeof ProfitLossReportOverview>;

export const ProfitLossReportEvents = Entries(ProfitLossEvents);

export type ProfitLossReportEvents = z.infer<typeof ProfitLossReportEvents>;

export type SelectedReport = {
  overview: ProfitLossOverview;
  entries: ProfitLossEvents;
  entriesLimit: number;
  entriesFound: number;
  lastProcessedTimestamp: number;
  processedActions: number;
  totalActions: number;
  start: number;
  end: number;
  firstProcessedTimestamp: number;
  settings: BaseAccountingSettings;
};

export interface ProfitLossReportPeriod {
  readonly start: number;
  readonly end: number;
}

export interface ProfitLossReportDebugPayload {
  fromTimestamp: number;
  toTimestamp: number;
  directoryPath?: string;
}

export const MissingAcquisition = z.object({
  asset: z.string(),
  foundAmount: NumericString,
  missingAmount: NumericString,
  time: z.number()
});

export type MissingAcquisition = z.infer<typeof MissingAcquisition>;

export const MissingPrice = z.object({
  fromAsset: z.string(),
  toAsset: z.string(),
  time: z.number(),
  rateLimited: z.boolean()
});

export type MissingPrice = z.infer<typeof MissingPrice>;

export const ReportActionableItem = z.object({
  missingAcquisitions: z.array(MissingAcquisition),
  missingPrices: z.array(MissingPrice)
});

export type ReportActionableItem = z.infer<typeof ReportActionableItem>;

export type PeriodChangedEvent = {
  start: string;
  end: string;
};

export type SelectionChangedEvent = {
  readonly year: string | 'custom';
  readonly quarter: Quarter;
};
