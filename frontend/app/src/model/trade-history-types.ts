import { default as BigNumber } from 'bignumber.js';
import { bigNumberify, Zero } from '@/utils/bignumbers';

export interface ApiEventEntry {
  readonly is_virtual: boolean;
  readonly net_profit_or_loss: string;
  readonly paid_asset: string;
  readonly paid_in_asset: string;
  readonly paid_in_profit_currency: string;
  readonly received_asset: string;
  readonly received_in_asset: string;
  readonly taxable_amount: string;
  readonly taxable_bought_cost_in_profit_currency: string;
  readonly taxable_received_in_profit_currency: string;
  readonly time: number;
  readonly type: string;
  readonly location: string;
}

interface ApiTradeHistoryOverview {
  readonly ledger_actions_profit_loss: string;
  readonly loan_profit: string;
  readonly defi_profit_loss: string;
  readonly margin_positions_profit_loss: string;
  readonly settlement_losses: string;
  readonly ethereum_transaction_gas_costs: string;
  readonly asset_movement_fees: string;
  readonly general_trade_profit_loss: string;
  readonly taxable_trade_profit_loss: string;
  readonly total_taxable_profit_loss: string;
  readonly total_profit_loss: string;
}

export interface TradeHistory {
  readonly overview: ApiTradeHistoryOverview;
  readonly all_events: ApiEventEntry[];
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

export interface EventEntry {
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
  readonly time: number;
  readonly isVirtual: boolean;
}

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

//TODO: Migrate to auto conversion
export const convertTradeHistoryOverview = (
  overview: ApiTradeHistoryOverview
): ProfitLossOverviewData => ({
  loanProfit: bigNumberify(overview.loan_profit),
  marginPositionsProfitLoss: bigNumberify(
    overview.margin_positions_profit_loss
  ),
  settlementLosses: bigNumberify(overview.settlement_losses),
  defiProfitLoss: bigNumberify(overview.defi_profit_loss),
  ethereumTransactionGasCosts: bigNumberify(
    overview.ethereum_transaction_gas_costs
  ),
  ledgerActionsProfitLoss: bigNumberify(overview.ledger_actions_profit_loss),
  assetMovementFees: bigNumberify(overview.asset_movement_fees),
  generalTradeProfitLoss: bigNumberify(overview.general_trade_profit_loss),
  taxableTradeProfitLoss: bigNumberify(overview.taxable_trade_profit_loss),
  totalTaxableProfitLoss: bigNumberify(overview.total_taxable_profit_loss),
  totalProfitLoss: bigNumberify(overview.total_profit_loss)
});

export const convertEventEntry = (event: ApiEventEntry): EventEntry => ({
  location: event.location,
  type: event.type,
  paidInProfitCurrency: bigNumberify(event.paid_in_profit_currency),
  paidAsset: event.paid_asset,
  paidInAsset: bigNumberify(event.paid_in_asset),
  taxableAmount: bigNumberify(event.taxable_amount),
  taxableBoughtCostInProfitCurrency: bigNumberify(
    event.taxable_bought_cost_in_profit_currency
  ),
  receivedAsset: event.received_asset,
  taxableReceivedInProfitCurrency: bigNumberify(
    event.taxable_received_in_profit_currency
  ),
  receivedInAsset: bigNumberify(event.received_in_asset),
  netProfitOrLoss: bigNumberify(event.net_profit_or_loss),
  time: event.time,
  isVirtual: event.is_virtual
});
