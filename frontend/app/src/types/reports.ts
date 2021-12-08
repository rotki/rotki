import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { Entries } from '@/types/common';

export const ProfitLossOverview = z.object({
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

export type ProfitLossOverview = z.infer<typeof ProfitLossOverview>;

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
  costBasis: CostBasis.nullable(),
  time: z.number(),
  isVirtual: z.boolean()
});

export const Report = z
  .object({
    identifier: z.number(),
    firstProcessedTimestamp: z.number(),
    startTs: z.number(),
    endTs: z.number(),
    sizeOnDisk: z.number(),
    timestamp: z.number()
  })
  .extend(ProfitLossOverview.shape);

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
  start: number;
  end: number;
  firstProcessedTimestamp: number;
};

export interface ProfitLossReportPeriod {
  readonly start: number;
  readonly end: number;
}
