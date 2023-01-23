import { z } from 'zod';
import { EvmChainAddress } from '@/types/history/tx';

export const MESSAGE_WARNING = 'warning';
const MESSAGE_ERROR = 'error';

const MessageVerbosity = z.enum([MESSAGE_WARNING, MESSAGE_ERROR]);

const LegacyMessageData = z.object({
  verbosity: MessageVerbosity,
  value: z.string()
});

const BalanceSnapshotError = z.object({
  location: z.string(),
  error: z.string()
});

export const EvmTransactionsQueryStatus = {
  ACCOUNT_CHANGE: 'account_change',
  QUERYING_TRANSACTIONS: 'querying_transactions',
  QUERYING_TRANSACTIONS_STARTED: 'querying_transactions_started',
  QUERYING_INTERNAL_TRANSACTIONS: 'querying_internal_transactions',
  QUERYING_EVM_TOKENS_TRANSACTIONS: 'querying_evm_tokens_transactions',
  QUERYING_TRANSACTIONS_FINISHED: 'querying_transactions_finished'
} as const;

export type EvmTransactionsQueryStatus =
  typeof EvmTransactionsQueryStatus[keyof typeof EvmTransactionsQueryStatus];

export const EvmTransactionQueryData = z
  .object({
    status: z.nativeEnum(EvmTransactionsQueryStatus),
    period: z.array(z.number())
  })
  .merge(EvmChainAddress);

export type BalanceSnapshotError = z.infer<typeof BalanceSnapshotError>;
export type EvmTransactionQueryData = z.infer<typeof EvmTransactionQueryData>;

export const PremiumStatusUpdateData = z.object({
  expired: z.boolean(),
  isPremiumActive: z.boolean()
});
export type PremiumStatusUpdateData = z.infer<typeof PremiumStatusUpdateData>;

export const LoginStatusData = z.object({
  startDbVersion: z.number().nonnegative(),
  targetDbVersion: z.number().nonnegative(),
  currentUpgrade: z.object({
    currentStep: z.number().nonnegative(),
    fromDbVersion: z.number().nonnegative(),
    totalSteps: z.number().nonnegative()
  })
});

export type LoginStatusData = z.infer<typeof LoginStatusData>;

export const MigratedAddresses = z.array(EvmChainAddress);

export type MigratedAddresses = z.infer<typeof MigratedAddresses>;

export const SocketMessageType = {
  LEGACY: 'legacy',
  BALANCES_SNAPSHOT_ERROR: 'balance_snapshot_error',
  EVM_TRANSACTION_STATUS: 'evm_transaction_status',
  PREMIUM_STATUS_UPDATE: 'premium_status_update',
  LOGIN_STATUS: 'login_status',
  EVM_ADDRESS_MIGRATION: 'evm_address_migration'
} as const;

export type SocketMessageType =
  typeof SocketMessageType[keyof typeof SocketMessageType];

const LegacyWebsocketMessage = z.object({
  type: z.literal(SocketMessageType.LEGACY),
  data: LegacyMessageData
});

const BalancesSnapshotErrorMessage = z.object({
  type: z.literal(SocketMessageType.BALANCES_SNAPSHOT_ERROR),
  data: BalanceSnapshotError
});

const EvmTransactionStatusMessage = z.object({
  type: z.literal(SocketMessageType.EVM_TRANSACTION_STATUS),
  data: EvmTransactionQueryData
});

const PremiumStatusUpdateMessage = z.object({
  type: z.literal(SocketMessageType.PREMIUM_STATUS_UPDATE),
  data: PremiumStatusUpdateData
});

const LoginStatusMessage = z.object({
  type: z.literal(SocketMessageType.LOGIN_STATUS),
  data: LoginStatusData
});

const MigratedAccountsMessage = z.object({
  type: z.literal(SocketMessageType.EVM_ADDRESS_MIGRATION),
  data: MigratedAddresses
});

export const WebsocketMessage = LegacyWebsocketMessage.or(
  BalancesSnapshotErrorMessage
)
  .or(EvmTransactionStatusMessage)
  .or(PremiumStatusUpdateMessage)
  .or(LoginStatusMessage)
  .or(MigratedAccountsMessage);

export type WebsocketMessage = z.infer<typeof WebsocketMessage>;
