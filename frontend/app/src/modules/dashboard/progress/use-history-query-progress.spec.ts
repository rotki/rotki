import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus, TransactionsQueryStatus } from '@/modules/core/messaging/types';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { type TxQueryStatusData, useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';
import { useHistoryQueryProgress } from './use-history-query-progress';

function setTxStatuses(statuses: Record<string, TxQueryStatusData>): void {
  const { queryStatus } = storeToRefs(useTxQueryStatusStore());
  set(queryStatus, statuses);
}

function setEventStatuses(statuses: Record<string, HistoryEventsQueryData>): void {
  const { queryStatus } = storeToRefs(useEventsQueryStatusStore());
  set(queryStatus, statuses);
}

function evmTx(status: TransactionsQueryStatus, address = '0xabc', chain = 'eth'): TxQueryStatusData {
  return {
    address,
    chain,
    period: [0, 1000],
    status,
    subtype: 'evm',
  };
}

function bitcoinTx(status: TransactionsQueryStatus, address = 'bc1'): TxQueryStatusData {
  return {
    address,
    chain: 'btc',
    status,
    subtype: 'bitcoin',
  };
}

function eventStatus(status: HistoryEventsQueryStatus, name = 'kraken', location = 'kraken'): HistoryEventsQueryData {
  return {
    eventType: '',
    location,
    name,
    period: [0, 1000],
    status,
  };
}

describe('useHistoryQueryProgress', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should return undefined when there are no statuses', () => {
    const { progress } = useHistoryQueryProgress();
    expect(get(progress)).toBeUndefined();
  });

  it('should report an active transaction with chain and address details', () => {
    setTxStatuses({
      a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS, '0xabc', 'eth'),
    });

    const { progress } = useHistoryQueryProgress();
    const value = get(progress);

    expect(value).toBeDefined();
    expect(value?.currentOperationData?.type).toBe('transaction');
    expect(value?.currentOperationData?.address).toBe('0xabc');
    expect(value?.currentOperationData?.chain).toBe('eth');
    expect(value?.currentStep).toBe(0);
    expect(value?.totalSteps).toBe(1);
    expect(value?.percentage).toBe(0);
  });

  it('should treat bitcoin as finished only at DECODING_TRANSACTIONS_FINISHED', () => {
    setTxStatuses({
      a: bitcoinTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      b: bitcoinTx(TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED, 'bc2'),
    });

    const { progress } = useHistoryQueryProgress();
    const value = get(progress);

    expect(value?.currentOperationData?.type).toBe('transaction');
    expect(value?.currentStep).toBe(1);
    expect(value?.totalSteps).toBe(2);
    expect(value?.percentage).toBe(50);
  });

  it('should treat non-bitcoin as finished at QUERYING_TRANSACTIONS_FINISHED', () => {
    setTxStatuses({
      a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x1'),
      b: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS, '0x2'),
    });

    const { progress } = useHistoryQueryProgress();
    const value = get(progress);

    expect(value?.currentOperationData?.address).toBe('0x2');
    expect(value?.currentStep).toBe(1);
    expect(value?.totalSteps).toBe(2);
    expect(value?.percentage).toBe(50);
  });

  it('should count cancelled transactions as finished and skip them as active', () => {
    setTxStatuses({
      a: evmTx(TransactionsQueryStatus.CANCELLED, '0x1'),
      b: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x2'),
    });

    const { progress } = useHistoryQueryProgress();
    const value = get(progress);

    expect(value?.currentOperation).toBeNull();
    expect(value?.currentOperationData).toBeNull();
    expect(value?.currentStep).toBe(2);
    expect(value?.totalSteps).toBe(2);
    expect(value?.percentage).toBe(100);
  });

  // eslint-disable-next-line complexity
  it('should fall back to an active event when no transactions are active', () => {
    setTxStatuses({
      a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x1'),
    });
    setEventStatuses({
      k: eventStatus(HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED, 'kraken', 'kraken'),
    });

    const { progress } = useHistoryQueryProgress();
    const value = get(progress);

    expect(value?.currentOperationData?.type).toBe('event');
    expect(value?.currentOperationData?.name).toBe('kraken');
    expect(value?.currentOperationData?.location).toBe('kraken');
    expect(value?.currentOperation).toContain('kraken');
    expect(value?.currentStep).toBe(1);
    expect(value?.totalSteps).toBe(2);
    expect(value?.percentage).toBe(50);
  });

  it('should count cancelled events as finished', () => {
    setEventStatuses({
      k: eventStatus(HistoryEventsQueryStatus.CANCELLED, 'kraken'),
      b: eventStatus(HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED, 'binance', 'binance'),
    });

    const { progress } = useHistoryQueryProgress();
    const value = get(progress);

    expect(value?.currentOperation).toBeNull();
    expect(value?.currentStep).toBe(2);
    expect(value?.totalSteps).toBe(2);
    expect(value?.percentage).toBe(100);
  });

  it('should prefer transactions over events when both are active', () => {
    setTxStatuses({
      a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS, '0xabc'),
    });
    setEventStatuses({
      k: eventStatus(HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED, 'kraken'),
    });

    const { progress } = useHistoryQueryProgress();
    const value = get(progress);

    expect(value?.currentOperationData?.type).toBe('transaction');
    expect(value?.totalSteps).toBe(2);
    expect(value?.currentStep).toBe(0);
  });
});
