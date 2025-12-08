import { type HistoryEventEntryType, NumericString } from '@rotki/common';
import { z } from 'zod/v4';

const LiquityStakingEventExtraData = z.object({
  asset: z.string(),
  stakedAmount: NumericString,
});

export enum TransactionChainType {
  EVM = 'evm',
  EVMLIKE = 'evmlike',
  BITCOIN = 'bitcoin',
  SOLANA = 'solana',
}

export const TransactionChainTypeNeedDecoding: TransactionChainType[] = [
  TransactionChainType.EVM,
  TransactionChainType.EVMLIKE,
  TransactionChainType.SOLANA,
] as const;

export interface TransactionRequestPayload {
  readonly accounts: BlockchainAddress[];
}

export interface PullLocationTransactionPayload {
  readonly transactions: LocationAndTxRef[];
  readonly deleteCustom?: boolean;
}

export interface PullEthBlockEventPayload {
  readonly blockNumbers: number[];
}

export type PullEventPayload = {
  type: typeof HistoryEventEntryType.ETH_BLOCK_EVENT;
  data: number [];
} | {
  type: typeof HistoryEventEntryType.EVM_SWAP_EVENT | typeof HistoryEventEntryType.EVM_EVENT | typeof HistoryEventEntryType.SOLANA_EVENT | typeof HistoryEventEntryType.SOLANA_SWAP_EVENT;
  data: LocationAndTxRef;
};

export interface ChainAndTxRefs {
  readonly chain: string;
  readonly txRefs: string[];
}

export interface PullTransactionPayload extends ChainAndTxRefs {
  readonly deleteCustom?: boolean;
}

export interface LocationAndTxRef {
  readonly location: string;
  readonly txRef: string;
}

export interface AddTransactionHashPayload {
  readonly blockchain: string;
  readonly txRef: string;
  readonly associatedAddress: string;
}

export const EvmChainAddress = z.object({
  address: z.string(),
  evmChain: z.string(),
});

export type EvmChainAddress = z.infer<typeof EvmChainAddress>;

export const BlockchainAddress = z.object({
  address: z.string(),
  blockchain: z.string().optional(),
});

export type BlockchainAddress = z.infer<typeof BlockchainAddress>;

interface TimeRange {
  readonly fromTimestamp?: number;
  readonly toTimestamp?: number;
}

export interface RepullingTransactionPayload extends TimeRange {
  readonly chain: string;
  readonly address?: string;
}

export interface RepullingTransactionResponse {
  newTransactionsCount: number;
}

export interface RepullingExchangeEventsPayload extends TimeRange {
  location: string;
  name: string;
}

export interface RepullingExchangeEventsResponse {
  queriedEvents: number;
  storedEvents: number;
  skippedEvents: number;
  actualEndTs: number;
}

export const EvmChainLikeAddress = z.object({
  address: z.string(),
  chain: z.string(),
});

export type EvmChainLikeAddress = z.infer<typeof EvmChainLikeAddress>;

export const ChainAddress = z.object({
  address: z.string(),
  chain: z.string(),
});

export type ChainAddress = z.infer<typeof ChainAddress>;

export const HistoryEventDetail = z
  .object({
    liquityStaking: LiquityStakingEventExtraData,
  })
  .nullish();

export type HistoryEventDetail = z.infer<typeof HistoryEventDetail>;

export const SkippedHistoryEventsSummary = z.object({
  locations: z.record(z.string(), z.number()),
  total: z.number(),
});

export type SkippedHistoryEventsSummary = z.infer<typeof SkippedHistoryEventsSummary>;

export const ProcessSkippedHistoryEventsResponse = z.object({
  successful: z.number(),
  total: z.number(),
});

export type ProcessSkippedHistoryEventsResponse = z.infer<typeof ProcessSkippedHistoryEventsResponse>;
