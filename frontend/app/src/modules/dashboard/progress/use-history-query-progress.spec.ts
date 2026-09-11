import { submitRefresh } from '@test/utils/history-refresh';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { type HistoryEventsQueryData, HistoryEventsQueryStatus, TransactionsQueryStatus } from '@/modules/core/messaging/types';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { type TxQueryStatusData, useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';
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
    // The orchestrator is a shared singleton, so its records outlive a test without this.
    useTaskOrchestrator().reset();
  });

  /**
   * Whether to render at all, and the numbers inside, now read the same source. Gating on the
   * stores instead disagreed with the body in both directions.
   */
  describe('visibility', () => {
    it('should show nothing when no refresh has been declared', () => {
      expect(get(useHistoryQueryProgress().progress)).toBeUndefined();
    });

    it('should appear as soon as the flow declares its work, before any message arrives', async () => {
      await submitRefresh({ eth: { '0x123': 'running' } });

      const value = get(useHistoryQueryProgress().progress);

      expect(value).toBeDefined();
      expect(value?.totalSteps).toBe(1);
      expect(value?.currentOperation).toBeNull();
    });

    it('should show nothing when the stores hold a run the ledger no longer has', () => {
      setTxStatuses({ a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS, '0x123') });

      expect(get(useHistoryQueryProgress().progress)).toBeUndefined();
    });
  });

  /**
   * Which item is being worked on, and its caption.
   *
   * Still read from the websocket stores: they are the only source that knows *which* address or
   * exchange a message was about. The counts beside it come from the ledger; see the next block.
   */
  describe('the active item', () => {
    /**
     * The indicator only renders while the flow has declared work, so every case here needs a
     * refresh in the ledger. What it *is* does not matter: these cases are about which item the
     * caption names, and the caption comes from the stores.
     */
    beforeEach(async () => {
      await submitRefresh({ eth: { '0xdeclared': 'running' } });
    });

    it('should report an active transaction with chain and address details', () => {
      setTxStatuses({
        a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS, '0xabc', 'eth'),
      });

      const value = get(useHistoryQueryProgress().progress);

      expect(value?.currentOperationData?.type).toBe('transaction');
      expect(value?.currentOperationData?.address).toBe('0xabc');
      expect(value?.currentOperationData?.chain).toBe('eth');
    });

    it('should treat bitcoin as active while it is decoding', () => {
      setTxStatuses({
        a: bitcoinTx(TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED),
        b: bitcoinTx(TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED, 'bc2'),
      });

      const value = get(useHistoryQueryProgress().progress);

      expect(value?.currentOperationData?.type).toBe('transaction');
      expect(value?.currentOperationData?.address).toBe('bc1');
    });

    it('should treat bitcoin as finished at QUERYING_TRANSACTIONS_FINISHED, since an empty query skips the decode messages', () => {
      setTxStatuses({
        a: bitcoinTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        b: bitcoinTx(TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED, 'bc2'),
      });

      expect(get(useHistoryQueryProgress().progress)?.currentOperation).toBeNull();
    });

    it('should treat non-bitcoin as finished at QUERYING_TRANSACTIONS_FINISHED', () => {
      setTxStatuses({
        a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x1'),
        b: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS, '0x2'),
      });

      expect(get(useHistoryQueryProgress().progress)?.currentOperationData?.address).toBe('0x2');
    });

    it('should skip a cancelled transaction when picking the active one', () => {
      setTxStatuses({
        a: evmTx(TransactionsQueryStatus.CANCELLED, '0x1'),
        b: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x2'),
      });

      const value = get(useHistoryQueryProgress().progress);

      expect(value?.currentOperation).toBeNull();
      expect(value?.currentOperationData).toBeNull();
    });

    it('should skip a failed transaction when picking the active one', () => {
      setTxStatuses({
        a: evmTx(TransactionsQueryStatus.FAILED, '0x1'),
        b: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x2'),
      });

      const value = get(useHistoryQueryProgress().progress);

      expect(value?.currentOperation).toBeNull();
      expect(value?.currentOperationData).toBeNull();
    });

    it('should fall back to an active event when no transactions are active', () => {
      setTxStatuses({
        a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x1'),
      });
      setEventStatuses({
        k: eventStatus(HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED, 'kraken', 'kraken'),
      });

      const value = get(useHistoryQueryProgress().progress);

      expect(value?.currentOperationData?.type).toBe('event');
      expect(value?.currentOperationData?.name).toBe('kraken');
      expect(value?.currentOperationData?.location).toBe('kraken');
      expect(value?.currentOperation).toContain('kraken');
    });

    it('should treat a cancelled event as finished when picking the active one', () => {
      setEventStatuses({
        k: eventStatus(HistoryEventsQueryStatus.CANCELLED, 'kraken'),
        b: eventStatus(HistoryEventsQueryStatus.QUERYING_EVENTS_FINISHED, 'binance', 'binance'),
      });

      expect(get(useHistoryQueryProgress().progress)?.currentOperation).toBeNull();
    });

    it('should prefer transactions over events when both are active', () => {
      setTxStatuses({
        a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS, '0xabc'),
      });
      setEventStatuses({
        k: eventStatus(HistoryEventsQueryStatus.QUERYING_EVENTS_STARTED, 'kraken'),
      });

      expect(get(useHistoryQueryProgress().progress)?.currentOperationData?.type).toBe('transaction');
    });
  });

  /**
   * How far along the refresh is.
   *
   * Read from the ledger, so the dashboard and the sync panel cannot disagree. Counting the stores
   * instead made the denominator grow as addresses and exchanges were reported, so the bar fell
   * whenever new work appeared.
   */
  describe('progress counts', () => {
    it('should count settled leaves over the leaves the flow declared', async () => {
      setTxStatuses({ a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS, '0x123') });
      await submitRefresh({ eth: { '0x123': 'complete', '0x456': 'running' } });

      const value = get(useHistoryQueryProgress().progress);

      expect(value?.currentStep).toBe(1);
      expect(value?.totalSteps).toBe(2);
      expect(value?.percentage).toBe(50);
    });

    it('should reach 100% only once every declared leaf has settled', async () => {
      setTxStatuses({ a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x123') });
      await submitRefresh({ eth: { '0x123': 'complete', '0x456': 'cancelled' } });

      const value = get(useHistoryQueryProgress().progress);

      expect(value?.currentStep).toBe(2);
      expect(value?.totalSteps).toBe(2);
      expect(value?.percentage).toBe(100);
    });

    /**
     * The denominator is fixed at submit time, so reporting a *new* address mid-run cannot make the
     * bar fall. Under the old store-derived count this case dropped from 100% to 50%.
     */
    it('should not fall when the stores learn of an address the flow did not declare', async () => {
      setTxStatuses({ a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x123') });
      await submitRefresh({ eth: { '0x123': 'complete' } });
      expect(get(useHistoryQueryProgress().progress)?.percentage).toBe(100);

      setTxStatuses({
        a: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, '0x123'),
        b: evmTx(TransactionsQueryStatus.QUERYING_TRANSACTIONS, '0xlate'),
      });

      expect(get(useHistoryQueryProgress().progress)?.percentage).toBe(100);
    });
  });
});
