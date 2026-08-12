import type { ComputedRef, Ref } from 'vue';
import type { TxQueryStatusData } from '@/modules/history/use-tx-query-status-store';
import { TransactionsQueryStatus } from '@/modules/core/messaging/types';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import { type AddressProgress, AddressStatus, AddressStep, type ChainProgress } from './types';

/**
 * Lookups rather than switches: a `Record` keyed by the status union is still exhaustive (a new
 * status is a compile error here, exactly as a missing `case` was) without every added state
 * costing another branch against the complexity cap.
 */
const ADDRESS_STATUS: Record<TransactionsQueryStatus, AddressStatus> = {
  [TransactionsQueryStatus.ACCOUNT_CHANGE]: AddressStatus.PENDING,
  [TransactionsQueryStatus.CANCELLED]: AddressStatus.CANCELLED,
  [TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED]: AddressStatus.COMPLETE,
  [TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED]: AddressStatus.DECODING,
  [TransactionsQueryStatus.FAILED]: AddressStatus.FAILED,
  [TransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS]: AddressStatus.QUERYING,
  [TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: AddressStatus.QUERYING,
  [TransactionsQueryStatus.QUERYING_TRANSACTIONS]: AddressStatus.QUERYING,
  [TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: AddressStatus.COMPLETE,
  [TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: AddressStatus.QUERYING,
};

/** Which sub-step a querying address is on; terminal and pending states have none. */
const ADDRESS_STEP: Record<TransactionsQueryStatus, AddressStep | undefined> = {
  [TransactionsQueryStatus.ACCOUNT_CHANGE]: undefined,
  [TransactionsQueryStatus.CANCELLED]: undefined,
  [TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED]: undefined,
  [TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED]: undefined,
  [TransactionsQueryStatus.FAILED]: undefined,
  [TransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS]: AddressStep.TOKENS,
  [TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: AddressStep.INTERNAL,
  [TransactionsQueryStatus.QUERYING_TRANSACTIONS]: AddressStep.TRANSACTIONS,
  [TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: undefined,
  [TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: undefined,
};

function mapStatus(status: TransactionsQueryStatus): AddressStatus {
  return ADDRESS_STATUS[status];
}

function mapStep(status: TransactionsQueryStatus): AddressStep | undefined {
  return ADDRESS_STEP[status];
}

function calculatePeriodProgress(period?: [number, number], originalPeriodEnd?: number, originalPeriodStart?: number): number | undefined {
  if (!period || !originalPeriodEnd)
    return undefined;

  const [periodStart, current] = period;
  // Use originalPeriodStart (first non-zero value) if available, otherwise fall back to period start
  const effectiveStart = originalPeriodStart ?? periodStart;
  const totalRange = originalPeriodEnd - effectiveStart;

  if (totalRange <= 0)
    return 100;

  const progressRange = current - effectiveStart;
  return Math.min(100, Math.max(0, Math.round((progressRange / totalRange) * 100)));
}

function toAddressProgress(data: TxQueryStatusData): AddressProgress {
  const { originalPeriodEnd, originalPeriodStart, period } = data;

  return {
    address: data.address,
    originalPeriodEnd,
    originalPeriodStart,
    period,
    periodProgress: data.status === TransactionsQueryStatus.CANCELLED ? undefined : calculatePeriodProgress(period, originalPeriodEnd, originalPeriodStart),
    status: mapStatus(data.status),
    step: mapStep(data.status),
  };
}

/**
 * Addresses that will not change again: succeeded, cancelled or failed.
 *
 * Exported because "terminal counts as done" was written out by hand at three separate call sites,
 * so adding a terminal state fixed some of them and silently left the others behind: the sync
 * banner sat at 93% forever while the chain list it summarised had already settled.
 */
export function settledAddresses(chain: Pick<ChainProgress, 'cancelled' | 'completed' | 'failed'>): number {
  return chain.completed + chain.cancelled + chain.failed;
}

/** Whether every one of a chain's addresses has reached a terminal state. */
export function isChainSettled(chain: Pick<ChainProgress, 'cancelled' | 'completed' | 'failed' | 'total'>): boolean {
  return chain.total > 0 && settledAddresses(chain) === chain.total;
}

function isDone(status: AddressStatus): boolean {
  // Failed counts as done, like cancelled: no further progress is coming for that address. Same
  // argument `percentageOf` makes for activities: a bar that excluded failures would stall short
  // of the end whenever a chain failed, and never reach a settled state.
  return status === AddressStatus.COMPLETE
    || status === AddressStatus.CANCELLED
    || status === AddressStatus.FAILED;
}

function calculateChainProgress(addresses: AddressProgress[]): number {
  if (addresses.length === 0)
    return 0;

  const done = addresses.filter(a => isDone(a.status)).length;
  return Math.round((done / addresses.length) * 100);
}

export function useChainProgress(
  queryStatus: Ref<Record<string, TxQueryStatusData>> | ComputedRef<Record<string, TxQueryStatusData>>,
): ComputedRef<ChainProgress[]> {
  const { isAddressExcluded } = useDisabledChains();

  return computed<ChainProgress[]>(() => {
    const statusMap = get(queryStatus);
    const grouped = new Map<string, { key: string; data: TxQueryStatusData }[]>();

    for (const [key, item] of Object.entries(statusMap)) {
      // Dropped before grouping so an excluded chain leaves no row *and* no denominator: these
      // entries are backend websocket status, not work we submitted, so the backend still reports
      // on chains the user switched off. Per address, not per chain - the setting excludes single
      // addresses on an otherwise active chain, and those must not pad the chain's total either.
      if (isAddressExcluded(item.chain, item.address))
        continue;

      const chain = item.chain.toLowerCase();
      if (!grouped.has(chain)) {
        grouped.set(chain, []);
      }
      grouped.get(chain)!.push({ data: item, key });
    }

    return Array.from(grouped.entries()).map(([chain, items]): ChainProgress => {
      const addresses = items.map(({ data }) => toAddressProgress(data));
      let completed = 0;
      let cancelledCount = 0;
      let failedCount = 0;
      let inProgress = 0;
      let pending = 0;

      for (const a of addresses) {
        switch (a.status) {
          case AddressStatus.COMPLETE:
            completed++;
            break;
          case AddressStatus.CANCELLED:
            cancelledCount++;
            break;
          case AddressStatus.FAILED:
            failedCount++;
            break;
          case AddressStatus.QUERYING:
          case AddressStatus.DECODING:
            inProgress++;
            break;
          case AddressStatus.PENDING:
            pending++;
            break;
        }
      }

      return {
        addresses,
        cancelled: cancelledCount,
        chain,
        completed,
        failed: failedCount,
        inProgress,
        pending,
        progress: calculateChainProgress(addresses),
        total: addresses.length,
      };
    }).sort((a, b) => {
      // Sort by: in-progress first, then by chain name
      if (a.inProgress > 0 && b.inProgress === 0)
        return -1;
      if (b.inProgress > 0 && a.inProgress === 0)
        return 1;
      return a.chain.localeCompare(b.chain);
    });
  });
}
