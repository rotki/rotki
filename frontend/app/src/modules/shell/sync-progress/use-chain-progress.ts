import type { ComputedRef, Ref } from 'vue';
import type { TxQueryStatusData } from '@/modules/history/use-tx-query-status-store';
import { TransactionsQueryStatus } from '@/modules/core/messaging/types';
import { type AddressProgress, AddressStatus, AddressStep, type ChainProgress } from './types';

function mapStatus(status: TransactionsQueryStatus): AddressStatus {
  switch (status) {
    case TransactionsQueryStatus.ACCOUNT_CHANGE:
      return AddressStatus.PENDING;
    case TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED:
    case TransactionsQueryStatus.QUERYING_TRANSACTIONS:
    case TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS:
    case TransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS:
      return AddressStatus.QUERYING;
    case TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED:
      return AddressStatus.DECODING;
    case TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED:
    case TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED:
      return AddressStatus.COMPLETE;
    case TransactionsQueryStatus.CANCELLED:
      return AddressStatus.CANCELLED;
  }
}

function mapStep(status: TransactionsQueryStatus): AddressStep | undefined {
  switch (status) {
    case TransactionsQueryStatus.QUERYING_TRANSACTIONS:
      return AddressStep.TRANSACTIONS;
    case TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS:
      return AddressStep.INTERNAL;
    case TransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS:
      return AddressStep.TOKENS;
    case TransactionsQueryStatus.ACCOUNT_CHANGE:
    case TransactionsQueryStatus.CANCELLED:
    case TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED:
    case TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED:
    case TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED:
    case TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED:
      return undefined;
  }
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
  const period = 'period' in data ? data.period : undefined;
  const originalPeriodEnd = 'originalPeriodEnd' in data ? data.originalPeriodEnd : undefined;
  const originalPeriodStart = 'originalPeriodStart' in data ? data.originalPeriodStart : undefined;

  return {
    address: data.address,
    originalPeriodEnd,
    originalPeriodStart,
    period,
    periodProgress: data.status === TransactionsQueryStatus.CANCELLED ? undefined : calculatePeriodProgress(period, originalPeriodEnd, originalPeriodStart),
    status: mapStatus(data.status),
    step: mapStep(data.status),
    subtype: data.subtype,
  };
}

function isDone(status: AddressStatus): boolean {
  return status === AddressStatus.COMPLETE || status === AddressStatus.CANCELLED;
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
  return computed<ChainProgress[]>(() => {
    const statusMap = get(queryStatus);
    const grouped = new Map<string, { key: string; data: TxQueryStatusData }[]>();

    for (const [key, item] of Object.entries(statusMap)) {
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
