import type { ChainAddress } from '@/modules/history/events/event-payloads';
import {
  TransactionsQueryStatus,
  type UnifiedTransactionStatusData,
} from '@/modules/messaging/types';
import { createQueryStatusState } from '@/store/history/query-status/index';
import { millisecondsToSeconds } from '@/utils/date';

type EvmlikeStatusStep = 'started' | 'finished';

interface BaseTxQueryStatusData {
  address: string;
  chain: string;
  status: TransactionsQueryStatus;
}

interface EvmTxQueryStatusData extends BaseTxQueryStatusData {
  subtype: 'evm';
  period: [number, number];
  originalPeriodEnd?: number;
  originalPeriodStart?: number;
}

interface EvmlikeTxQueryStatusData extends BaseTxQueryStatusData {
  subtype: 'evmlike';
  period: [number, number];
  originalPeriodEnd?: number;
  originalPeriodStart?: number;
}

interface BitcoinTxQueryStatusData extends BaseTxQueryStatusData {
  subtype: 'bitcoin';
}

interface SolanaTxQueryStatusData extends BaseTxQueryStatusData {
  subtype: 'solana';
  period: [number, number];
  originalPeriodEnd?: number;
  originalPeriodStart?: number;
}

export type TxQueryStatusData = EvmTxQueryStatusData | EvmlikeTxQueryStatusData | BitcoinTxQueryStatusData | SolanaTxQueryStatusData;

export function isBitcoinTxQueryStatusData(data: TxQueryStatusData): data is BitcoinTxQueryStatusData {
  return data.subtype === 'bitcoin';
}

/**
 * Determines the original period end value for progress tracking.
 * For STARTED status, captures the period[1] as the end boundary.
 * For subsequent updates, preserves the existing value.
 */
function determineOriginalPeriodEnd(
  status: TransactionsQueryStatus,
  period: [number, number],
  existing?: TxQueryStatusData,
): number | undefined {
  if (status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED) {
    return period[1];
  }
  if (existing && 'originalPeriodEnd' in existing) {
    return existing.originalPeriodEnd;
  }
  return undefined;
}

/**
 * Determines the original period start value for progress tracking.
 * - If period[0] > 0, uses that as the actual start
 * - If period[0] is 0 (beginning of time), captures the first non-zero period[1] as the effective start
 * - Preserves existing originalPeriodStart for subsequent updates
 * - Does not capture from STARTED status (where period[1] is the end boundary, not progress)
 */
function determineOriginalPeriodStart(
  status: TransactionsQueryStatus,
  period: [number, number],
  existing?: TxQueryStatusData,
): number | undefined {
  const [periodStart, periodCurrent] = period;

  if (periodStart > 0) {
    return periodStart;
  }
  if (existing && 'originalPeriodStart' in existing && existing.originalPeriodStart !== undefined) {
    return existing.originalPeriodStart;
  }
  if (periodCurrent > 0 && status !== TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED) {
    return periodCurrent;
  }
  return undefined;
}

export const useTxQueryStatusStore = defineStore('history/transaction-query-status', () => {
  const createKey = ({ address, chain }: ChainAddress): string => address + chain.toLowerCase();

  const isStatusFinished = (item: TxQueryStatusData): boolean => {
    if (item.status === TransactionsQueryStatus.CANCELLED)
      return true;

    if (isBitcoinTxQueryStatusData(item)) {
      return item.status === TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED;
    }
    return item.status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;
  };

  const {
    isAllFinished,
    markCancelled,
    queryStatus,
    removeQueryStatus: remove,
    resetQueryStatus,
    stopSyncing,
    syncing,
  } = createQueryStatusState<TxQueryStatusData>(isStatusFinished, createKey);

  const initializeQueryStatus = (data: ChainAddress[]): void => {
    resetQueryStatus();
    set(syncing, true);

    const status = { ...get(queryStatus) };
    const now = millisecondsToSeconds(Date.now());
    for (const item of data) {
      const key = createKey(item);
      status[key] = {
        address: item.address,
        chain: item.chain,
        originalPeriodEnd: now,
        period: [0, now],
        status: TransactionsQueryStatus.ACCOUNT_CHANGE,
        subtype: 'evm' as const,
      };
    }
    set(queryStatus, status);
  };

  const removeQueryStatus = (data: ChainAddress): void => {
    remove(createKey({ address: data.address, chain: data.chain }));
  };

  const setUnifiedTxQueryStatus = (data: UnifiedTransactionStatusData): void => {
    if (!get(syncing))
      return;

    if (data.status === TransactionsQueryStatus.ACCOUNT_CHANGE) {
      return;
    }

    const statuses = { ...get(queryStatus) };
    const chain = data.chain.toLowerCase();

    if (data.subtype === 'bitcoin') {
      // Convert bitcoin transactions (with addresses array) to individual entries
      for (const address of data.addresses) {
        const key = createKey({ address, chain });
        // Guard: don't overwrite cancelled entries
        if (statuses[key]?.status === TransactionsQueryStatus.CANCELLED)
          continue;

        statuses[key] = {
          address,
          chain,
          status: data.status,
          subtype: 'bitcoin' as const,
        };
      }
    }
    else {
      // Handle EVM/EvmLike/Solana transactions (with single address)
      const key = createKey({ address: data.address, chain });
      const existing = statuses[key];

      // Guard: don't overwrite cancelled entries
      if (existing?.status === TransactionsQueryStatus.CANCELLED) {
        return;
      }

      statuses[key] = {
        address: data.address,
        chain,
        originalPeriodEnd: determineOriginalPeriodEnd(data.status, data.period, existing),
        originalPeriodStart: determineOriginalPeriodStart(data.status, data.period, existing),
        period: data.period,
        status: data.status,
        subtype: data.subtype,
      };
    }

    set(queryStatus, statuses);
  };

  /**
   * Manually set evmlike chain status since they don't send websocket messages.
   * Call with 'started' before the API call and 'finished' after.
   */
  const setEvmlikeStatus = (account: ChainAddress, step: EvmlikeStatusStep): void => {
    const status = { ...get(queryStatus) };
    const chain = account.chain.toLowerCase();
    const key = createKey({ address: account.address, chain });

    // Guard: don't overwrite cancelled entries
    if (status[key]?.status === TransactionsQueryStatus.CANCELLED)
      return;

    const now = millisecondsToSeconds(Date.now());

    if (step === 'started') {
      status[key] = {
        address: account.address,
        chain,
        originalPeriodEnd: now,
        period: [0, now],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED,
        subtype: 'evmlike' as const,
      };
    }
    else {
      const existing = status[key];
      const originalPeriodEnd = existing && 'originalPeriodEnd' in existing ? existing.originalPeriodEnd : now;

      status[key] = {
        address: account.address,
        chain,
        originalPeriodEnd,
        period: [0, now],
        status: TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED,
        subtype: 'evmlike' as const,
      };
    }

    set(queryStatus, status);
  };

  const markAddressCancelled = (account: ChainAddress): void => {
    const key = createKey(account);
    const existing = get(queryStatus)[key];
    if (existing) {
      markCancelled(key, { ...existing, status: TransactionsQueryStatus.CANCELLED });
    }
  };

  const isAddressCancelled = (account: ChainAddress): boolean =>
    get(queryStatus)[createKey(account)]?.status === TransactionsQueryStatus.CANCELLED;

  return {
    initializeQueryStatus,
    isAddressCancelled,
    isAllFinished,
    isStatusFinished,
    markAddressCancelled,
    queryStatus,
    removeQueryStatus,
    resetQueryStatus,
    setEvmlikeStatus,
    setUnifiedTxQueryStatus,
    stopSyncing,
    syncing,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useTxQueryStatusStore, import.meta.hot));
