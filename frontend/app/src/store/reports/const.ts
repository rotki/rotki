import {
  ProfitLossOverviewData,
  ReportError,
  ReportPeriod
} from '@rotki/common/lib/reports';
import { Zero } from '@/utils/bignumbers';

export enum ReportActions {
  FETCH_REPORTS = 'fetchReports',
  FETCH_REPORT = 'fetchReport',
  DELETE_REPORT = 'deleteReport'
}

export enum ReportMutations {
  SET_REPORT_ID = 'setReportId',
  SET_REPORTS = 'setReports',
  CURRENCY = 'currency',
  REPORT_PERIOD = 'reportPeriod',
  ACCOUNTING_SETTINGS = 'accountingSettings',
  RESET = 'reset',
  PROGRESS = 'progress',
  REPORT_ERROR = 'reportError'
}

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
