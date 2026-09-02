import type { ChainAddress } from '@/modules/history/events/event-payloads';
import { millisecondsToSeconds } from '@/modules/core/common/data/date';
import { logger } from '@/modules/core/common/logging/logging';
import {
  TransactionsQueryStatus,
  type UnifiedTransactionStatusData,
} from '@/modules/core/messaging/types';
import { createQueryStatusState } from '@/modules/history/create-query-status-state';
import {
  bitcoinPeriodFields,
  determineOriginalPeriodEnd,
  determineOriginalPeriodStart,
  type PeriodTracking,
  periodWithCursorAtStart,
} from '@/modules/history/tx-query-status-period';

type EvmlikeStatusStep = 'started' | 'finished';

/**
 * Subtype for a synthesized failure entry. `TransactionChainType`'s values are exactly these
 * strings, so a caller can pass the chain type it already has.
 */
type FailedSubtype = TxQueryStatusData['subtype'];

interface BaseTxQueryStatusData {
  address: string;
  chain: string;
  status: TransactionsQueryStatus;
}

interface EvmTxQueryStatusData extends BaseTxQueryStatusData, PeriodTracking {
  subtype: 'evm';
}

interface EvmlikeTxQueryStatusData extends BaseTxQueryStatusData, PeriodTracking {
  subtype: 'evmlike';
}

/** `PeriodTracking` is partial only because the backend does not send bitcoin a period yet. */
interface BitcoinTxQueryStatusData extends BaseTxQueryStatusData, Partial<PeriodTracking> {
  subtype: 'bitcoin';
}

interface SolanaTxQueryStatusData extends BaseTxQueryStatusData, PeriodTracking {
  subtype: 'solana';
}

export type TxQueryStatusData = EvmTxQueryStatusData | EvmlikeTxQueryStatusData | BitcoinTxQueryStatusData | SolanaTxQueryStatusData;

/** An account plus the subtype its chain queries under, which decides the shape of its entry. */
export interface SeededAccount extends ChainAddress {
  subtype: TxQueryStatusData['subtype'];
}

function isBitcoinTxQueryStatusData(data: TxQueryStatusData): data is BitcoinTxQueryStatusData {
  return data.subtype === 'bitcoin';
}

/**
 * Whether an address will report no further progress.
 *
 * The single source of truth — the sync panel and the dashboard indicator both read this. A second
 * copy of the rule is how the panel once called a bitcoin address complete while the indicator still
 * counted it as querying.
 *
 * Bitcoin decodes inline, so it can end on either finish message: the backend sends
 * `QUERYING_TRANSACTIONS_FINISHED` on both the empty and the decoding path and reaches
 * `DECODING_TRANSACTIONS_FINISHED` only on the latter. Accepting both settles the empty path, at the
 * cost of reading complete for the moment between the two.
 */
export function isTxQueryStatusFinished(item: TxQueryStatusData): boolean {
  if (item.status === TransactionsQueryStatus.CANCELLED || item.status === TransactionsQueryStatus.FAILED)
    return true;

  if (isBitcoinTxQueryStatusData(item)) {
    return item.status === TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED
      || item.status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;
  }

  return item.status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED;
}

export const useTxQueryStatusStore = defineStore('history/transaction-query-status', () => {
  const createKey = ({ address, chain }: ChainAddress): string => address + chain.toLowerCase();

  const isStatusFinished = isTxQueryStatusFinished;

  const {
    isAllFinished,
    markTerminal,
    queryStatus,
    removeQueryStatus: remove,
    resetQueryStatus,
    stopSyncing,
    syncing,
  } = createQueryStatusState<TxQueryStatusData>(isStatusFinished, createKey);

  /**
   * Seed the panel with the addresses a sync is about to query.
   *
   * `extend` keeps what an earlier wave of the *same* sync produced. A refresh runs in waves (late
   * accounts are drained into a follow-up run, each wave carrying only its own), so replacing the map
   * drops every address the previous wave finished and the denominator falls mid-sync.
   *
   * An address already present is left alone. Re-seeding it as `ACCOUNT_CHANGE` walks a finished
   * chain's progress backwards, the same lie in the other direction.
   */
  const initializeQueryStatus = (data: SeededAccount[], { extend = false }: { extend?: boolean } = {}): void => {
    if (!extend)
      resetQueryStatus();

    set(syncing, true);

    const status = { ...get(queryStatus) };
    const now = millisecondsToSeconds(Date.now());
    for (const item of data) {
      const key = createKey(item);
      if (extend && status[key])
        continue;

      const base = {
        address: item.address,
        chain: item.chain,
        status: TransactionsQueryStatus.ACCOUNT_CHANGE,
      };

      status[key] = item.subtype === 'bitcoin'
        ? { ...base, subtype: item.subtype }
        : { ...base, originalPeriodEnd: now, period: [0, now], subtype: item.subtype };
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
      // One batched message covers every address, so it fans out into an entry each.
      for (const address of data.addresses) {
        const key = createKey({ address, chain });
        const existing = statuses[key];
        // Guard: don't overwrite cancelled entries
        if (existing?.status === TransactionsQueryStatus.CANCELLED)
          continue;

        statuses[key] = {
          address,
          chain,
          status: data.status,
          subtype: 'bitcoin' as const,
          ...bitcoinPeriodFields(data, existing),
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
        period: periodWithCursorAtStart(data.status, data.period),
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

    const current = status[key]?.status;
    if (current === TransactionsQueryStatus.CANCELLED || current === TransactionsQueryStatus.FAILED)
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
      markTerminal(key, { ...existing, status: TransactionsQueryStatus.CANCELLED });
    }
  };

  /**
   * Record that an address's query failed.
   *
   * Marked, not removed. The chain list is derived from these entries, so removing a failure makes
   * a chain whose every address failed vanish from the panel along with its denominator, leaving the
   * run reading "11/11 chains complete".
   *
   * A missing entry is created, not dropped. A per-address query normally announces itself first
   * (`with_tx_status_messaging` sends STARTED), but not when the task failed before reaching any
   * address or when the run's messages never landed. Returning early there hides the chain, which is
   * the state this exists to prevent.
   */
  const markAddressFailed = (account: ChainAddress, subtype: FailedSubtype = 'evm'): void => {
    const key = createKey(account);
    const existing = get(queryStatus)[key];
    if (existing) {
      markTerminal(key, { ...existing, status: TransactionsQueryStatus.FAILED });
      return;
    }

    logger.warn(
      `marking ${account.address} on ${account.chain} as failed with no status entry to mark; `
      + 'the query failed before it announced itself, or its progress messages never arrived',
    );

    const now = millisecondsToSeconds(Date.now());
    const period: [number, number] = [0, now];
    const base = {
      address: account.address,
      chain: account.chain.toLowerCase(),
      status: TransactionsQueryStatus.FAILED,
    };

    set(queryStatus, {
      ...get(queryStatus),
      [key]: subtype === 'bitcoin'
        ? { ...base, subtype }
        : { ...base, originalPeriodEnd: now, period, subtype },
    });
  };

  const isAddressCancelled = (account: ChainAddress): boolean =>
    get(queryStatus)[createKey(account)]?.status === TransactionsQueryStatus.CANCELLED;

  return {
    initializeQueryStatus,
    isAddressCancelled,
    isAllFinished,
    isStatusFinished,
    markAddressCancelled,
    markAddressFailed,
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
