import BigNumber from 'bignumber.js';
import { bigNumberify, Zero } from '@/utils/bignumbers';

export interface ApiEventEntry {
  readonly type: string;
  readonly paid_in_profit_currency: string;
  readonly paid_asset: string;
  readonly paid_in_asset: string;
  readonly taxable_amount: string;
  readonly taxable_bought_cost: string;
  readonly received_asset: string;
  readonly received_in_profit_currency: string;
  readonly received_in_asset: string;
  readonly net_profit_or_loss: string;
  readonly time: number;
  readonly is_virtual: boolean;
}

export interface ApiTradeHistoryOverview {
  readonly loan_profit: string;
  readonly margin_positions_profit_loss: string;
  readonly settlement_losses: string;
  readonly ethereum_transaction_gas_costs: string;
  readonly asset_movement_fees: string;
  readonly general_trade_profit_loss: string;
  readonly taxable_trade_profit_loss: string;
  readonly total_taxable_profit_loss: string;
  readonly total_profit_loss: string;
}

export interface TradeHistoryResult {
  readonly overview: ApiTradeHistoryOverview;
  readonly all_events: ApiEventEntry[];
  readonly error?: string;
}

export interface TradeHistoryOverview {
  readonly loanProfit: BigNumber;
  readonly marginPositionsProfitLoss: BigNumber;
  readonly settlementLosses: BigNumber;
  readonly ethereumTransactionGasCosts: BigNumber;
  readonly assetMovementFees: BigNumber;
  readonly generalTradeProfitLoss: BigNumber;
  readonly taxableTradeProfitLoss: BigNumber;
  readonly totalTaxableProfitLoss: BigNumber;
  readonly totalProfitLoss: BigNumber;
}

export interface EventEntry {
  readonly type: string;
  readonly paidInProfitCurrency: BigNumber;
  readonly paidAsset: string;
  readonly paidInAsset: BigNumber;
  readonly taxableAmount: BigNumber;
  readonly taxableBoughtCost: BigNumber;
  readonly receivedAsset: string;
  readonly receivedInProfitCurrency: BigNumber;
  readonly receivedInAsset: BigNumber;
  readonly netProfitOrLoss: BigNumber;
  readonly time: number;
  readonly isVirtual: boolean;
}

export const tradeHistoryPlaceholder = (): TradeHistoryOverview => ({
  loanProfit: Zero,
  marginPositionsProfitLoss: Zero,
  settlementLosses: Zero,
  ethereumTransactionGasCosts: Zero,
  assetMovementFees: Zero,
  generalTradeProfitLoss: Zero,
  taxableTradeProfitLoss: Zero,
  totalTaxableProfitLoss: Zero,
  totalProfitLoss: Zero
});

export const convertTradeHistoryOverview = (
  overview: ApiTradeHistoryOverview
): TradeHistoryOverview => ({
  loanProfit: bigNumberify(overview.loan_profit),
  marginPositionsProfitLoss: bigNumberify(
    overview.margin_positions_profit_loss
  ),
  settlementLosses: bigNumberify(overview.settlement_losses),
  ethereumTransactionGasCosts: bigNumberify(
    overview.ethereum_transaction_gas_costs
  ),
  assetMovementFees: bigNumberify(overview.asset_movement_fees),
  generalTradeProfitLoss: bigNumberify(overview.general_trade_profit_loss),
  taxableTradeProfitLoss: bigNumberify(overview.taxable_trade_profit_loss),
  totalTaxableProfitLoss: bigNumberify(overview.total_taxable_profit_loss),
  totalProfitLoss: bigNumberify(overview.total_profit_loss)
});

export const convertEventEntry = (event: ApiEventEntry): EventEntry => ({
  type: event.type,
  paidInProfitCurrency: bigNumberify(event.paid_in_profit_currency),
  paidAsset: event.paid_asset,
  paidInAsset: bigNumberify(event.paid_in_asset),
  taxableAmount: bigNumberify(event.taxable_amount),
  taxableBoughtCost: bigNumberify(event.taxable_bought_cost),
  receivedAsset: event.received_asset,
  receivedInProfitCurrency: bigNumberify(event.received_in_profit_currency),
  receivedInAsset: bigNumberify(event.received_asset),
  netProfitOrLoss: bigNumberify(event.net_profit_or_loss),
  time: event.time,
  isVirtual: event.is_virtual
});
