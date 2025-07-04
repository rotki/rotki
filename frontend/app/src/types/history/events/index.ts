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
}

export interface TransactionRequestPayload {
  readonly accounts: BlockchainAddress[];
}

export interface PullEvmTransactionPayload {
  readonly transactions: EvmChainAndTxHash[];
  readonly deleteCustom?: boolean;
}

export interface PullEthBlockEventPayload {
  readonly blockNumbers: number[];
}

export type PullEventPayload = {
  type: typeof HistoryEventEntryType.ETH_BLOCK_EVENT;
  data: number [];
} | {
  type: typeof HistoryEventEntryType.EVM_SWAP_EVENT | typeof HistoryEventEntryType.EVM_EVENT;
  data: EvmChainAndTxHash;
};

export interface PullEvmLikeTransactionPayload {
  readonly transactions: ChainAndTxHash[];
  readonly deleteCustom?: boolean;
}

export type PullTransactionPayload = PullEvmTransactionPayload | PullEvmLikeTransactionPayload;

export interface ChainAndTxHash {
  readonly chain: string;
  readonly txHash: string;
}

export interface EvmChainAndTxHash {
  readonly evmChain: string;
  readonly txHash: string;
}

export interface AddTransactionHashPayload extends EvmChainAndTxHash {
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

export interface RepullingTransactionPayload extends Partial<EvmChainAddress> {
  readonly fromTimestamp: number;
  readonly toTimestamp: number;
}

export interface RepullingTransactionResponse {
  newTransactionsCount: number;
}

export const EvmChainLikeAddress = z.object({
  address: z.string(),
  chain: z.string(),
});

export type EvmChainLikeAddress = z.infer<typeof EvmChainLikeAddress>;

export const BitcoinChainAddress = z.object({
  address: z.string(),
  chain: z.string(),
});

export type BitcoinChainAddress = z.infer<typeof BitcoinChainAddress>;

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
