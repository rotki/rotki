import type { PaginationRequestPayload } from '@/types/common';
import type { Quarter } from '@/types/settings/frontend-settings';
import { NumericString } from '@rotki/common';
import { z } from 'zod/v4';
import { CollectionCommonFields } from '@/types/collection';
import { BaseAccountingSettings } from '@/types/user';

export const ProfitLossOverviewItem = z.object({
  free: NumericString,
  taxable: NumericString,
});

export type ProfitLossOverviewItem = z.infer<typeof ProfitLossOverviewItem>;

export const ProfitLossOverview = z.record(z.string(), ProfitLossOverviewItem);

export type ProfitLossOverview = z.infer<typeof ProfitLossOverview>;

export const MatchedAcquisitionsEvent = z.object({
  fullAmount: NumericString,
  index: z.number(),
  rate: NumericString,
  timestamp: z.number(),
});

export type MatchedAcquisitionsEvent = z.infer<typeof MatchedAcquisitionsEvent>;

export const MatchedAcquisitions = z.object({
  amount: NumericString,
  event: MatchedAcquisitionsEvent,
  taxable: z.boolean(),
});

export type MatchedAcquisitions = z.infer<typeof MatchedAcquisitions>;

export const Report = z.object({
  endTs: z.number(),
  firstProcessedTimestamp: z.number(),
  identifier: z.number(),
  lastProcessedTimestamp: z.number(),
  overview: ProfitLossOverview,
  processedActions: z.number(),
  settings: BaseAccountingSettings,
  startTs: z.number(),
  timestamp: z.number(),
  totalActions: z.number(),
});

export type Report = z.infer<typeof Report>;

export const CostBasis = z.object({
  isComplete: z.boolean().nullish(),
  matchedAcquisitions: z.array(MatchedAcquisitions).nullish(),
});

export type CostBasis = z.infer<typeof CostBasis>;

export const ProfitLossEvent = z.object({
  assetIdentifier: z.string(),
  costBasis: CostBasis.nullable(),
  freeAmount: NumericString,
  groupId: z.string().nullish(),
  location: z.string(),
  notes: z.string().nullable(),
  pnlFree: NumericString,
  pnlTaxable: NumericString,
  price: NumericString,
  taxableAmount: NumericString,
  timestamp: z.number(),
  type: z.string(),
});

export type ProfitLossEvent = z.infer<typeof ProfitLossEvent>;

const ProfitLossEvents = z.array(ProfitLossEvent);

export type ProfitLossEvents = z.infer<typeof ProfitLossEvents>;

export interface ProfitLossEventsPayload extends PaginationRequestPayload<ProfitLossEvent> {
  reportId: number;
}

export const ProfitLossEventsCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(ProfitLossEvent),
});

export const ReportProgress = z.object({
  processingState: z.string(),
  totalProgress: z.string(),
});

export type ReportProgress = z.infer<typeof ReportProgress>;

export interface ReportError {
  error: string;
  message: string;
}

export const Reports = z.object({
  entries: z.array(Report),
  entriesFound: z.number(),
  entriesLimit: z.number(),
});

export type Reports = z.infer<typeof Reports>;

export const ProfitLossReportOverview = z.object({
  entries: z.array(ProfitLossOverview),
  entriesFound: z.number(),
  entriesLimit: z.number(),
});

export type ProfitLossReportOverview = z.infer<typeof ProfitLossReportOverview>;

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
  originatingEventId: z.number().optional(),
  time: z.number(),
});

export type MissingAcquisition = z.infer<typeof MissingAcquisition>;

export const MissingPrice = z.object({
  fromAsset: z.string(),
  rateLimited: z.boolean().optional(),
  time: z.number(),
  toAsset: z.string(),
});

export type MissingPrice = z.infer<typeof MissingPrice>;

export interface EditableMissingPrice extends MissingPrice {
  price: string;
  saved: boolean;
  useRefreshedHistoricalPrice: boolean;
}

export const ReportActionableItem = z.object({
  missingAcquisitions: z.array(MissingAcquisition),
  missingPrices: z.array(MissingPrice),
});

export type ReportActionableItem = z.infer<typeof ReportActionableItem>;

export interface PeriodChangedEvent {
  start: number;
  end: number;
}

export interface SelectionChangedEvent {
  readonly year: string | 'custom';
  readonly quarter: Quarter;
}
