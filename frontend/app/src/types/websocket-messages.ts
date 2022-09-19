import { z } from 'zod';

export const MESSAGE_WARNING = 'warning';
const MESSAGE_ERROR = 'error';

const MessageVerbosity = z.enum([MESSAGE_WARNING, MESSAGE_ERROR]);

export const LegacyMessageData = z.object({
  verbosity: MessageVerbosity,
  value: z.string()
});

export type LegacyMessageData = z.infer<typeof LegacyMessageData>;

export const BalanceSnapshotError = z.object({
  location: z.string(),
  error: z.string()
});

export enum EthereumTransactionsQueryStatus {
  ACCOUNT_CHANGE = 'account_change',
  QUERYING_TRANSACTIONS = 'querying_transactions',
  QUERYING_TRANSACTIONS_STARTED = 'querying_transactions_started',
  QUERYING_INTERNAL_TRANSACTIONS = 'querying_internal_transactions',
  QUERYING_ETHEREUM_TOKENS_TRANSACTIONS = 'querying_ethereum_tokens_transactions',
  QUERYING_TRANSACTIONS_FINISHED = 'querying_transactions_finished'
}

export const EthereumTransactionQueryData = z.object({
  status: z.nativeEnum(EthereumTransactionsQueryStatus),
  address: z.string(),
  period: z.array(z.number())
});

export type BalanceSnapshotError = z.infer<typeof BalanceSnapshotError>;
export type EthereumTransactionQueryData = z.infer<
  typeof EthereumTransactionQueryData
>;

export const PremiumStatusUpdateData = z.object({
  expired: z.boolean(),
  is_premium_active: z.boolean()
});
export type PremiumStatusUpdateData = z.infer<typeof PremiumStatusUpdateData>;

export enum SocketMessageType {
  LEGACY = 'legacy',
  BALANCES_SNAPSHOT_ERROR = 'balance_snapshot_error',
  ETHEREUM_TRANSACTION_STATUS = 'ethereum_transaction_status',
  PREMIUM_STATUS_UPDATE = 'premium_status_update'
}

type MessageData = {
  [SocketMessageType.LEGACY]: LegacyMessageData;
  [SocketMessageType.BALANCES_SNAPSHOT_ERROR]: BalanceSnapshotError;
  [SocketMessageType.ETHEREUM_TRANSACTION_STATUS]: EthereumTransactionQueryData;
  [SocketMessageType.PREMIUM_STATUS_UPDATE]: PremiumStatusUpdateData;
};

export interface WebsocketMessage<T extends SocketMessageType> {
  readonly type: T;
  readonly data: MessageData[T];
}
