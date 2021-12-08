import { ProfitLossOverview, ReportError } from '@/types/reports';
import { Zero } from '@/utils/bignumbers';

export const emptyError: () => ReportError = () => ({
  error: '',
  message: ''
});

export const pnlOverview = (): ProfitLossOverview => ({
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
