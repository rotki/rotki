import { type EvmChainAndTxHash } from '@/types/history/events';

export const useHistoryTransactionsForm = createSharedComposable(
  useForm<EvmChainAndTxHash | null>
);
