export interface EvmTransaction {
  evmChain: string;
  txHash: string;
}
export enum IgnoreActionType {
  TRADES = 'trade',
  MOVEMENTS = 'asset_movement',
  EVM_TRANSACTIONS = 'evm_transaction',
  LEDGER_ACTIONS = 'ledger_action'
}

export interface CommonIgnorePayload {
  actionType: Exclude<IgnoreActionType, IgnoreActionType.EVM_TRANSACTIONS>;
  data: string[];
}

export interface EvmTxIgnorePayload {
  actionType: IgnoreActionType.EVM_TRANSACTIONS;
  data: EvmTransaction[];
}

export type IgnorePayload = CommonIgnorePayload | EvmTxIgnorePayload;
