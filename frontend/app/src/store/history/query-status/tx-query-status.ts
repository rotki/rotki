import type { BitcoinChainAddress, EvmChainAddress } from '@/types/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useQueryStatusStore } from '@/store/history/query-status/index';
import {
  TransactionsQueryStatus,
  type UnifiedTransactionStatusData,
} from '@/types/websocket-messages';

interface BaseTxQueryStatusData {
  address: string;
  chain: string;
  status: TransactionsQueryStatus;
}

export interface EvmTxQueryStatusData extends BaseTxQueryStatusData {
  subtype: 'evm';
  period: [number, number];
}

export interface EvmlikeTxQueryStatusData extends BaseTxQueryStatusData {
  subtype: 'evmlike';
  period: [number, number];
}

export interface BitcoinTxQueryStatusData extends BaseTxQueryStatusData {
  subtype: 'bitcoin';
}

export type TxQueryStatusData = EvmTxQueryStatusData | EvmlikeTxQueryStatusData | BitcoinTxQueryStatusData;

export function isEvmTxQueryStatusData(data: TxQueryStatusData): data is EvmTxQueryStatusData {
  return data.subtype === 'evm';
}

export function isEvmlikeTxQueryStatusData(data: TxQueryStatusData): data is EvmlikeTxQueryStatusData {
  return data.subtype === 'evmlike';
}

export function isBitcoinTxQueryStatusData(data: TxQueryStatusData): data is BitcoinTxQueryStatusData {
  return data.subtype === 'bitcoin';
}

export const useTxQueryStatusStore = defineStore('history/transaction-query-status', () => {
  const { getChain } = useSupportedChains();

  const createKey = ({ address, chain }: { address: string; chain: string }): string => address + chain;

  const isStatusFinished = (item: TxQueryStatusData): boolean => {
    if (isBitcoinTxQueryStatusData(item)) {
      return item.status === TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED;
    }
    return item.status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;
  };

  const {
    isAllFinished,
    queryStatus,
    removeQueryStatus: remove,
    resetQueryStatus,
  } = useQueryStatusStore<TxQueryStatusData>(isStatusFinished, createKey);

  const initializeQueryStatus = (data: EvmChainAddress[]): void => {
    resetQueryStatus();

    const status = { ...get(queryStatus) };
    const now = Date.now() / 1000;
    for (const item of data) {
      const chain = getChain(item.evmChain);
      const key = createKey({ address: item.address, chain });
      status[key] = {
        address: item.address,
        chain,
        period: [0, now],
        status: TransactionsQueryStatus.ACCOUNT_CHANGE,
        subtype: 'evm' as const,
      };
    }
    set(queryStatus, status);
  };

  const removeQueryStatus = (data: EvmChainAddress | BitcoinChainAddress): void => {
    if ('evmChain' in data) {
      const chain = getChain(data.evmChain);
      remove(createKey({ address: data.address, chain }));
    }
    else {
      remove(createKey({ address: data.address, chain: data.chain }));
    }
  };

  const setUnifiedTxQueryStatus = (data: UnifiedTransactionStatusData): void => {
    if (data.status === TransactionsQueryStatus.ACCOUNT_CHANGE) {
      return;
    }

    const status = { ...get(queryStatus) };
    const chain = data.chain.toLowerCase();

    // Convert bitcoin transactions (with addresses array) to individual entries
    if (data.subtype === 'bitcoin') {
      for (const address of data.addresses) {
        const key = createKey({ address, chain });
        status[key] = {
          address,
          chain,
          status: data.status,
          subtype: 'bitcoin' as const,
        };
      }
    }
    else {
      // Handle EVM/EvmLike transactions (with single address)
      const key = createKey({ address: data.address, chain });
      status[key] = {
        address: data.address,
        chain,
        period: data.period,
        status: data.status,
        subtype: data.subtype,
      };
    }

    set(queryStatus, status);
  };

  return {
    initializeQueryStatus,
    isAllFinished,
    isStatusFinished,
    queryStatus,
    removeQueryStatus,
    resetQueryStatus,
    setUnifiedTxQueryStatus,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useTxQueryStatusStore, import.meta.hot));
