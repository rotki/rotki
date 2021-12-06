import { NumericString, PagedResourceParameters } from '@rotki/common';
import { z } from 'zod';

export type ReportPeriod = {
  start: number;
  end: number;
};

export const ProfitLossOverviewData = z.object({
  loanProfit: NumericString,
  defiProfitLoss: NumericString,
  marginPositionsProfitLoss: NumericString,
  ledgerActionsProfitLoss: NumericString,
  settlementLosses: NumericString,
  ethereumTransactionGasCosts: NumericString,
  assetMovementFees: NumericString,
  generalTradeProfitLoss: NumericString,
  taxableTradeProfitLoss: NumericString,
  totalTaxableProfitLoss: NumericString,
  totalProfitLoss: NumericString
});
export type ProfitLossOverviewData = z.infer<typeof ProfitLossOverviewData>;

export const MatchedAcquisitions = z.object({
  time: z.number(),
  description: z.string(),
  location: z.string(),
  amount: NumericString,
  rate: NumericString,
  feeRate: NumericString,
  usedAmount: NumericString
});

export const CostBasis = z.object({
  isComplete: z.boolean(),
  matchedAcquisitions: z.array(MatchedAcquisitions)
});
export type CostBasis = z.infer<typeof CostBasis>;

export const ProfitLossEvent = z.object({
  location: z.string(),
  type: z.string(),
  paidInProfitCurrency: NumericString,
  paidAsset: z.string(),
  paidInAsset: NumericString,
  taxableAmount: NumericString,
  taxableBoughtCostInProfitCurrency: NumericString,
  receivedAsset: z.string(),
  taxableReceivedInProfitCurrency: NumericString,
  receivedInAsset: NumericString,
  netProfitOrLoss: NumericString,
  costBasis: z.union([CostBasis, z.null()]),
  time: z.number(),
  isVirtual: z.boolean()
});

export type ProfitLossEvent = z.infer<typeof ProfitLossEvent>;

export const Report = z.object({
  identifier: z.number(),
  name: z.string(),
  timestamp: z.union([z.number(), z.null()]),
  startTs: z.number(),
  endTs: z.number(),
  sizeOnDisk: z.union([NumericString, z.null()])
});

export const TradeHistory = z.object({
  eventsProcessed: z.number(),
  eventsLimit: z.number(),
  firstProcessedTimestamp: z.number(),
  overview: ProfitLossOverviewData,
  allEvents: z.array(ProfitLossEvent),
  loaded: z.union([z.boolean(), z.undefined()])
});

export type TradeHistory = z.infer<typeof TradeHistory>;

export type Report = z.infer<typeof Report>;

export const TradeHistoryReport = TradeHistory.extend(Report.shape);

export const PagedReport = PagedResourceParameters.extend(
  TradeHistoryReport.shape
);
export type PagedReport = z.infer<typeof PagedReport>;

export const ReportProgress = z.object({
  processingState: z.string(),
  totalProgress: z.string()
});

export type ReportProgress = z.infer<typeof ReportProgress>;

export type ReportError = {
  error: string;
  message: string;
};

export const ReportsPayload = z.object({
  entries: z.array(Report),
  entriesFound: z.number(),
  entriesLimit: z.number()
});

export const ReportOverviewPayload = ReportsPayload.extend({
  entries: z.array(ProfitLossOverviewData)
});

export type ReportOverviewPayload = z.infer<typeof ReportOverviewPayload>;

export const ReportEventsPayload = ReportsPayload.extend({
  entries: z.array(ProfitLossEvent)
});

export const ReportsPayloadData = PagedResourceParameters.extend(
  ReportsPayload.shape
);

export type ReportsPayloadData = z.infer<typeof ReportsPayloadData>;

export const ReportOverviewPayloadData = PagedResourceParameters.extend(
  ReportOverviewPayload.shape
);

export type ReportOverviewPayloadData = z.infer<
  typeof ReportOverviewPayloadData
>;

export const ReportEventsPayloadData = PagedResourceParameters.extend(
  ReportEventsPayload.shape
);

export type ReportEventsPayloadData = z.infer<typeof ReportEventsPayloadData>;
