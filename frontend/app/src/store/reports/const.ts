import {
  ProfitLossOverviewData,
  ReportError,
  ReportPeriod
} from '@/store/reports/types';
import { Zero } from '@/utils/bignumbers';

export const MUTATION_PROGRESS = 'progress' as const;
export const MUTATION_REPORT_ERROR = 'reportError' as const;

export const emptyPeriod: () => ReportPeriod = () => ({
  start: 0,
  end: 0
});

export const emptyError: () => ReportError = () => ({
  error: '',
  message: ''
});

export const tradeHistoryPlaceholder = (): ProfitLossOverviewData => ({
  loanProfit: Zero,
  defiProfitLoss: Zero,
  marginPositionsProfitLoss: Zero,
  settlementLosses: Zero,
  ethereumTransactionGasCosts: Zero,
  ledgerActionsProfitLoss: Zero,
  assetMovementFees: Zero,
  generalTradeProfitLoss: Zero,
  taxableTradeProfitLoss: Zero,
  totalTaxableProfitLoss: Zero,
  totalProfitLoss: Zero
});
