import { default as BigNumber } from 'bignumber.js';
import { TradeLocation } from '@/services/history/types';

export type ReportPeriod = {
  readonly start: number;
  readonly end: number;
};

export type ReportData = {
  readonly overview: ProfitLossOverviewData;
  readonly events: ProfitLossEvent[];
  readonly limit: number;
  readonly processed: number;
  readonly firstProcessedTimestamp: number;
};

export interface TradeHistory {
  readonly eventsProcessed: number;
  readonly eventsLimit: number;
  readonly firstProcessedTimestamp: number;
  readonly overview: ProfitLossOverviewData;
  readonly allEvents: ProfitLossEvent[];
}

export interface ProfitLossOverviewData {
  readonly loanProfit: BigNumber;
  readonly defiProfitLoss: BigNumber;
  readonly marginPositionsProfitLoss: BigNumber;
  readonly ledgerActionsProfitLoss: BigNumber;
  readonly settlementLosses: BigNumber;
  readonly ethereumTransactionGasCosts: BigNumber;
  readonly assetMovementFees: BigNumber;
  readonly generalTradeProfitLoss: BigNumber;
  readonly taxableTradeProfitLoss: BigNumber;
  readonly totalTaxableProfitLoss: BigNumber;
  readonly totalProfitLoss: BigNumber;
}

interface MatchedAcquisition {
  readonly time: number;
  readonly description: string;
  readonly location: TradeLocation;
  readonly usedAmount: BigNumber;
  readonly amount: BigNumber;
  readonly rate: BigNumber;
  readonly feeRate: BigNumber;
}

interface CostBasis {
  readonly isComplete: boolean;
  readonly matchedAcquisitions: MatchedAcquisition[];
}

export interface ProfitLossEvent {
  readonly location: string;
  readonly type: string;
  readonly paidInProfitCurrency: BigNumber;
  readonly paidAsset: string;
  readonly paidInAsset: BigNumber;
  readonly taxableAmount: BigNumber;
  readonly taxableBoughtCostInProfitCurrency: BigNumber;
  readonly receivedAsset: string;
  readonly taxableReceivedInProfitCurrency: BigNumber;
  readonly receivedInAsset: BigNumber;
  readonly netProfitOrLoss: BigNumber;
  readonly costBasis: CostBasis | null;
  readonly time: number;
  readonly isVirtual: boolean;
}

export interface ReportProgress {
  readonly processingState: string;
  readonly totalProgress: string;
}

export type ReportError = {
  readonly error: string;
  readonly message: string;
};
