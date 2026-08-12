import type { TxQueryStatusData } from '@/modules/history/use-tx-query-status-store';
import { beforeEach, describe, expect, it } from 'vitest';
import { TransactionsQueryStatus } from '@/modules/core/messaging/types';
import { AddressStatus, AddressStep } from './types';
import { useChainProgress } from './use-chain-progress';

describe('useChainProgress', () => {
  const createEvmStatusData = (
    address: string,
    chain: string,
    status: TransactionsQueryStatus,
    period: [number, number] = [0, 1000],
    originalPeriodEnd?: number,
    originalPeriodStart?: number,
  ): TxQueryStatusData => ({
    address,
    chain,
    originalPeriodEnd,
    originalPeriodStart,
    period,
    status,
    subtype: 'evm',
  });

  const createBitcoinStatusData = (
    address: string,
    chain: string,
    status: TransactionsQueryStatus,
  ): TxQueryStatusData => ({
    address,
    chain,
    status,
    subtype: 'bitcoin',
  });

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  describe('status mapping', () => {
    it('should map ACCOUNT_CHANGE to PENDING status', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.ACCOUNT_CHANGE),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.PENDING);
    });

    it('should map QUERYING_TRANSACTIONS_STARTED to QUERYING status', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.QUERYING);
    });

    it('should map QUERYING_TRANSACTIONS to QUERYING status with TRANSACTIONS step', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.QUERYING);
      expect(chains[0].addresses[0].step).toBe(AddressStep.TRANSACTIONS);
    });

    it('should map QUERYING_INTERNAL_TRANSACTIONS to QUERYING status with INTERNAL step', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.QUERYING);
      expect(chains[0].addresses[0].step).toBe(AddressStep.INTERNAL);
    });

    it('should map QUERYING_EVM_TOKENS_TRANSACTIONS to QUERYING status with TOKENS step', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.QUERYING);
      expect(chains[0].addresses[0].step).toBe(AddressStep.TOKENS);
    });

    it('should map DECODING_TRANSACTIONS_STARTED to DECODING status', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.DECODING);
    });

    it('should map QUERYING_TRANSACTIONS_FINISHED to COMPLETE status', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.COMPLETE);
    });

    it('should map DECODING_TRANSACTIONS_FINISHED to COMPLETE status', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.COMPLETE);
    });

    it('should map CANCELLED to CANCELLED status', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.CANCELLED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.CANCELLED);
    });

    it('should map FAILED to FAILED status', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x123', 'eth', TransactionsQueryStatus.FAILED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].status).toBe(AddressStatus.FAILED);
    });
  });

  describe('failed addresses', () => {
    it('should keep a chain whose every address failed', () => {
      // The regression this guards: a failed sync used to REMOVE its query-status entry, and the
      // chain list is derived from those entries, so a chain that failed outright vanished from
      // the panel along with its own denominator. A run with three failed gnosis addresses read
      // "11/11 chains complete", all green.
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'gnosis', TransactionsQueryStatus.FAILED),
        key2: createEvmStatusData('0x222', 'gnosis', TransactionsQueryStatus.FAILED),
        key3: createEvmStatusData('0x333', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      });

      const chains = get(useChainProgress(queryStatus));

      expect(chains.map(c => c.chain).sort()).toStrictEqual(['eth', 'gnosis']);
      const gnosis = chains.find(c => c.chain === 'gnosis');
      expect(gnosis?.failed).toBe(2);
      expect(gnosis?.completed).toBe(0);
    });

    it('should count a failed address as done so the chain can settle', () => {
      // Same argument `percentageOf` makes for activities: no further progress is coming, so a bar
      // that excluded failures would stall short of the end and never settle.
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'gnosis', TransactionsQueryStatus.FAILED),
        key2: createEvmStatusData('0x222', 'gnosis', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      });

      const chains = get(useChainProgress(queryStatus));

      expect(chains[0].progress).toBe(100);
    });
  });

  describe('chain grouping', () => {
    it('should group addresses by chain', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        key2: createEvmStatusData('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        key3: createEvmStatusData('0x333', 'optimism', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains).toHaveLength(2);

      const ethChain = chains.find(c => c.chain === 'eth');
      const optimismChain = chains.find(c => c.chain === 'optimism');

      expect(ethChain?.addresses).toHaveLength(2);
      expect(optimismChain?.addresses).toHaveLength(1);
    });

    it('should normalize chain names to lowercase', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'ETH', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        key2: createEvmStatusData('0x222', 'Optimism', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains.map(c => c.chain)).toEqual(expect.arrayContaining(['eth', 'optimism']));
    });
  });

  describe('progress calculation', () => {
    it('should calculate chain progress based on completed addresses', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        key2: createEvmStatusData('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      const ethChain = chains.find(c => c.chain === 'eth');
      expect(ethChain?.completed).toBe(1);
      expect(ethChain?.inProgress).toBe(1);
      expect(ethChain?.total).toBe(2);
      expect(ethChain?.progress).toBe(50);
    });

    it('should return 0 progress for empty chain', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({});

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains).toHaveLength(0);
    });

    it('should return 100 progress when all addresses are complete', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        key2: createEvmStatusData('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      const ethChain = chains.find(c => c.chain === 'eth');
      expect(ethChain?.progress).toBe(100);
    });
  });

  describe('period progress calculation', () => {
    it('should calculate period progress when originalPeriodEnd and period are provided', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData(
          '0x123',
          'eth',
          TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          [0, 500],
          1000,
          0,
        ),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].periodProgress).toBe(50);
    });

    it('should return undefined when originalPeriodEnd is not provided', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData(
          '0x123',
          'eth',
          TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          [0, 500],
          undefined,
        ),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].periodProgress).toBeUndefined();
    });

    it('should use originalPeriodStart as effectiveStart when provided', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData(
          '0x123',
          'eth',
          TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          [100, 600],
          1000,
          200,
        ),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      // effectiveStart = 200, current = 600, originalPeriodEnd = 1000
      // totalRange = 1000 - 200 = 800
      // progressRange = 600 - 200 = 400
      // progress = (400 / 800) * 100 = 50
      expect(chains[0].addresses[0].periodProgress).toBe(50);
    });

    it('should return 100 when totalRange is 0', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData(
          '0x123',
          'eth',
          TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          [500, 500],
          500,
          500,
        ),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].periodProgress).toBe(100);
    });

    it('should cap progress at 100', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData(
          '0x123',
          'eth',
          TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          [0, 1500],
          1000,
          0,
        ),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].periodProgress).toBe(100);
    });

    it('should ensure progress is at least 0', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData(
          '0x123',
          'eth',
          TransactionsQueryStatus.QUERYING_TRANSACTIONS,
          [500, 100],
          1000,
          500,
        ),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      // effectiveStart = 500, current = 100, originalPeriodEnd = 1000
      // progressRange = 100 - 500 = -400 (negative)
      // Should be capped at 0
      expect(chains[0].addresses[0].periodProgress).toBe(0);
    });
  });

  describe('sorting', () => {
    it('should sort chains with in-progress addresses first', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'arbitrum', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        key2: createEvmStatusData('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        key3: createEvmStatusData('0x333', 'optimism', TransactionsQueryStatus.ACCOUNT_CHANGE),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      // eth has in-progress (QUERYING), should be first
      expect(chains[0].chain).toBe('eth');
    });

    it('should sort alphabetically when in-progress status is the same', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'zksync', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        key2: createEvmStatusData('0x222', 'arbitrum', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        key3: createEvmStatusData('0x333', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].chain).toBe('arbitrum');
      expect(chains[1].chain).toBe('eth');
      expect(chains[2].chain).toBe('zksync');
    });
  });

  describe('period handling', () => {
    // The progress bar is driven by the period alone, so an entry that carries none must produce
    // neither a period nor a progress value rather than defaulting to one.
    it('should leave period and progress unset for an entry without a period', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createBitcoinStatusData('bc1q...', 'btc', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      expect(chains[0].addresses[0].period).toBeUndefined();
      expect(chains[0].addresses[0].periodProgress).toBeUndefined();
    });
  });

  describe('cancelled status', () => {
    it('should map CANCELLED status entries to CANCELLED address status', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: { ...createEvmStatusData('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS), status: TransactionsQueryStatus.CANCELLED },
        key2: createEvmStatusData('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      const ethChain = chains.find(c => c.chain === 'eth');
      const cancelledAddress = ethChain?.addresses.find(a => a.address === '0x111');
      const activeAddress = ethChain?.addresses.find(a => a.address === '0x222');

      expect(cancelledAddress?.status).toBe(AddressStatus.CANCELLED);
      expect(activeAddress?.status).toBe(AddressStatus.QUERYING);
    });

    it('should count cancelled in chain progress', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: { ...createEvmStatusData('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS), status: TransactionsQueryStatus.CANCELLED },
        key2: createEvmStatusData('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
        key3: createEvmStatusData('0x333', 'eth', TransactionsQueryStatus.ACCOUNT_CHANGE),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      const ethChain = chains.find(c => c.chain === 'eth');
      expect(ethChain?.cancelled).toBe(1);
      expect(ethChain?.completed).toBe(1);
      expect(ethChain?.pending).toBe(1);
    });

    it('should treat cancelled as done for progress calculation', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: { ...createEvmStatusData('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS), status: TransactionsQueryStatus.CANCELLED },
        key2: createEvmStatusData('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      const ethChain = chains.find(c => c.chain === 'eth');
      expect(ethChain?.progress).toBe(100);
    });
  });

  describe('counts', () => {
    it('should correctly count pending, inProgress, and completed addresses', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'eth', TransactionsQueryStatus.ACCOUNT_CHANGE),
        key2: createEvmStatusData('0x222', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
        key3: createEvmStatusData('0x333', 'eth', TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED),
        key4: createEvmStatusData('0x444', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      });

      const result = useChainProgress(queryStatus);
      const chains = get(result);

      const ethChain = chains.find(c => c.chain === 'eth');
      expect(ethChain?.pending).toBe(1);
      expect(ethChain?.inProgress).toBe(2); // QUERYING + DECODING
      expect(ethChain?.completed).toBe(1);
      expect(ethChain?.total).toBe(4);
    });
  });

  describe('reactivity', () => {
    it('should update when queryStatus changes', () => {
      const queryStatus = ref<Record<string, TxQueryStatusData>>({
        key1: createEvmStatusData('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS),
      });

      const result = useChainProgress(queryStatus);

      expect(get(result)[0].addresses[0].status).toBe(AddressStatus.QUERYING);

      // Update status
      set(queryStatus, {
        key1: createEvmStatusData('0x111', 'eth', TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED),
      });

      expect(get(result)[0].addresses[0].status).toBe(AddressStatus.COMPLETE);
    });
  });
});
