import {
  ProfitLossOverviewData,
  ReportError,
  ReportPeriod
} from '@/types/reports';
import { Zero } from '@/utils/bignumbers';

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
