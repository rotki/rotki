import { CommonQueryStatusData } from '@rotki/common';
import { z } from 'zod/v4';
import { SocketMessageProgressUpdateSubType } from './base';

export const TransactionsQueryStatus = {
  ACCOUNT_CHANGE: 'account_change',
  DECODING_TRANSACTIONS_FINISHED: 'decoding_transactions_finished',
  DECODING_TRANSACTIONS_STARTED: 'decoding_transactions_started',
  QUERYING_EVM_TOKENS_TRANSACTIONS: 'querying_evm_tokens_transactions',
  QUERYING_INTERNAL_TRANSACTIONS: 'querying_internal_transactions',
  QUERYING_TRANSACTIONS: 'querying_transactions',
  QUERYING_TRANSACTIONS_FINISHED: 'querying_transactions_finished',
  QUERYING_TRANSACTIONS_STARTED: 'querying_transactions_started',
} as const;

export type TransactionsQueryStatus = (typeof TransactionsQueryStatus)[keyof typeof TransactionsQueryStatus];

export const EvmTransactionStatusData = z.object({
  address: z.string(),
  chain: z.string(),
  period: z.tuple([z.number(), z.number()]),
  status: z.enum(TransactionsQueryStatus),
  subtype: z.literal('evm').or(z.literal('evmlike')),
});

export const BitcoinTransactionStatusData = z.object({
  addresses: z.array(z.string()),
  chain: z.string(),
  status: z.enum(TransactionsQueryStatus),
  subtype: z.literal('bitcoin'),
});

export const UnifiedTransactionStatusData = z.union([
  EvmTransactionStatusData,
  BitcoinTransactionStatusData,
]);

export type UnifiedTransactionStatusData = z.infer<typeof UnifiedTransactionStatusData>;

export const EvmUnDecodedTransactionsData = CommonQueryStatusData.extend({
  chain: z.string(),
});

export type EvmUnDecodedTransactionsData = z.infer<typeof EvmUnDecodedTransactionsData>;

export const EvmUnDecodedTransactionsDataWithSubtype = EvmUnDecodedTransactionsData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.EVM_UNDECODED_TRANSACTIONS),
});

export const EvmUndecodedTransactionBreakdown = z.object({
  total: z.number(),
  undecoded: z.number(),
});

export const EvmUndecodedTransactionResponse = z.record(z.string(), EvmUndecodedTransactionBreakdown);

export type EvmUndecodedTransactionResponse = z.infer<typeof EvmUndecodedTransactionResponse>;
