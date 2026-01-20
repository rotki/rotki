import type { ComputedRef, Ref } from 'vue';
import type { TxQueryStatusData } from '@/store/history/query-status/tx-query-status';
import { TransactionsQueryStatus } from '@/modules/messaging/types';
import { type AddressProgress, AddressStatus, AddressStep, type ChainProgress } from '../types';

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
    periodProgress: calculatePeriodProgress(period, originalPeriodEnd, originalPeriodStart),
    status: mapStatus(data.status),
    step: mapStep(data.status),
    subtype: data.subtype,
  };
}

function isComplete(status: AddressStatus): boolean {
  return status === AddressStatus.COMPLETE;
}

function isInProgress(status: AddressStatus): boolean {
  return status === AddressStatus.QUERYING || status === AddressStatus.DECODING;
}

function isPending(status: AddressStatus): boolean {
  return status === AddressStatus.PENDING;
}

function calculateChainProgress(addresses: AddressProgress[]): number {
  if (addresses.length === 0)
    return 0;

  const completed = addresses.filter(a => isComplete(a.status)).length;
  return Math.round((completed / addresses.length) * 100);
}

export function useChainProgress(
  queryStatus: Ref<Record<string, TxQueryStatusData>> | ComputedRef<Record<string, TxQueryStatusData>>,
): ComputedRef<ChainProgress[]> {
  return computed<ChainProgress[]>(() => {
    const statusMap = get(queryStatus);
    const grouped = new Map<string, TxQueryStatusData[]>();

    for (const item of Object.values(statusMap)) {
      const chain = item.chain.toLowerCase();
      if (!grouped.has(chain)) {
        grouped.set(chain, []);
      }
      grouped.get(chain)!.push(item);
    }

    return Array.from(grouped.entries()).map(([chain, items]): ChainProgress => {
      const addresses = items.map(toAddressProgress);
      const completed = addresses.filter(a => isComplete(a.status)).length;
      const inProgress = addresses.filter(a => isInProgress(a.status)).length;
      const pending = addresses.filter(a => isPending(a.status)).length;

      return {
        addresses,
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
