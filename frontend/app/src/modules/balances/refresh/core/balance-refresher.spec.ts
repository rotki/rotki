import { hasTag } from 'plainfp/tagged';
import { assert, describe, expect, it, vi } from 'vitest';
import { createBalanceRefresher } from './balance-refresher';
import { type BalanceRefreshPorts, RefreshSource } from './refresh-types';

interface Deferred {
  readonly promise: Promise<void>;
  readonly resolve: () => void;
}

function deferred(): Deferred {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function createPorts(overrides: Partial<BalanceRefreshPorts> = {}): BalanceRefreshPorts {
  return {
    detectTokens: vi.fn<(chains: readonly string[]) => Promise<void>>(async () => {}),
    queryBanks: vi.fn<() => Promise<void>>(async () => {}),
    queryChains: vi.fn<(chains: readonly string[]) => Promise<void>>(async () => {}),
    queryExchanges: vi.fn<() => Promise<void>>(async () => {}),
    queryManual: vi.fn<() => Promise<void>>(async () => {}),
    redetectByDefault: () => false,
    refreshPrices: vi.fn<() => Promise<void>>(async () => {}),
    supportedChains: () => ['eth', 'btc'],
    supportsDetection: chain => chain === 'eth',
    ...overrides,
  };
}

describe('createBalanceRefresher', () => {
  describe('refreshBlockchain', () => {
    it('should query every supported chain by default', async () => {
      const ports = createPorts();
      const outcome = await createBalanceRefresher(ports).refreshBlockchain();

      expect(outcome.ok).toBe(true);
      expect(ports.queryChains).toHaveBeenCalledExactlyOnceWith(['eth', 'btc']);
      expect(ports.detectTokens).not.toHaveBeenCalled();
    });

    it('should detect on detection chains and still query the others when redetecting', async () => {
      const ports = createPorts();
      await createBalanceRefresher(ports).refreshBlockchain({ redetect: true });

      expect(ports.detectTokens).toHaveBeenCalledExactlyOnceWith(['eth']);
      expect(ports.queryChains).toHaveBeenCalledExactlyOnceWith(['btc']);
    });

    it('should follow the user default when the caller does not choose', async () => {
      const ports = createPorts({ redetectByDefault: () => true });
      await createBalanceRefresher(ports).refreshBlockchain({ chains: ['eth'] });

      expect(ports.detectTokens).toHaveBeenCalledExactlyOnceWith(['eth']);
      expect(ports.queryChains).not.toHaveBeenCalled();
    });

    it('should report a failing port instead of rejecting', async () => {
      const cause = new Error('rpc down');
      const ports = createPorts({ queryChains: async () => Promise.reject(cause) });
      const outcome = await createBalanceRefresher(ports).refreshBlockchain();

      assert(!outcome.ok);
      expect(outcome.error).toHaveLength(1);
      expect(hasTag(outcome.error[0], 'RefreshFailed')).toBe(true);
      expect(outcome.error[0]).toMatchObject({ cause, source: RefreshSource.BLOCKCHAIN });
    });

    it('should report a port that throws while planning', async () => {
      const ports = createPorts({
        supportedChains: () => {
          throw new Error('chains unavailable');
        },
      });
      const outcome = await createBalanceRefresher(ports).refreshBlockchain();

      assert(!outcome.ok);
      expect(outcome.error[0]).toMatchObject({ source: RefreshSource.BLOCKCHAIN });
      expect(ports.queryChains).not.toHaveBeenCalled();
    });
  });

  describe('refreshAll', () => {
    it('should refresh chains, exchanges, banks and manual balances, then prices', async () => {
      const ports = createPorts();
      const outcome = await createBalanceRefresher(ports).refreshAll();

      expect(outcome.ok).toBe(true);
      expect(ports.queryChains).toHaveBeenCalledOnce();
      expect(ports.queryExchanges).toHaveBeenCalledOnce();
      expect(ports.queryBanks).toHaveBeenCalledOnce();
      expect(ports.queryManual).toHaveBeenCalledOnce();
      expect(ports.refreshPrices).toHaveBeenCalledOnce();
    });

    it('should start pricing only after the slowest source has settled', async () => {
      const exchanges = deferred();
      const ports = createPorts({ queryExchanges: async () => exchanges.promise });
      const running = createBalanceRefresher(ports).refreshAll();

      await vi.waitFor(() => expect(ports.queryBanks).toHaveBeenCalledOnce());
      await Promise.resolve();
      expect(ports.refreshPrices).not.toHaveBeenCalled();

      exchanges.resolve();
      await running;
      expect(ports.refreshPrices).toHaveBeenCalledOnce();
    });

    it('should still price and name every failed source when some sources fail', async () => {
      const ports = createPorts({
        queryBanks: async () => Promise.reject(new Error('bank')),
        queryExchanges: () => {
          throw new Error('exchange');
        },
      });
      const outcome = await createBalanceRefresher(ports).refreshAll();

      expect(ports.refreshPrices).toHaveBeenCalledOnce();
      assert(!outcome.ok);
      expect(outcome.error.map(failure => failure.source)).toEqual([RefreshSource.EXCHANGES, RefreshSource.BANKS]);
    });

    it('should pass redetect through to the blockchain step', async () => {
      const ports = createPorts();
      await createBalanceRefresher(ports).refreshAll({ redetect: true });

      expect(ports.detectTokens).toHaveBeenCalledExactlyOnceWith(['eth']);
      expect(ports.queryChains).toHaveBeenCalledExactlyOnceWith(['btc']);
    });
  });

  describe('refreshSource', () => {
    it.each([
      { query: 'queryExchanges', source: RefreshSource.EXCHANGES },
      { query: 'queryBanks', source: RefreshSource.BANKS },
      { query: 'queryManual', source: RefreshSource.MANUAL },
    ] as const)('should query only $source and then prices', async ({ query, source }) => {
      const ports = createPorts();
      const outcome = await createBalanceRefresher(ports).refreshSource(source);

      expect(outcome.ok).toBe(true);
      for (const port of ['queryExchanges', 'queryBanks', 'queryManual'] as const) {
        if (port === query)
          expect(ports[port]).toHaveBeenCalledOnce();
        else
          expect(ports[port]).not.toHaveBeenCalled();
      }
      expect(ports.queryChains).not.toHaveBeenCalled();
      expect(ports.detectTokens).not.toHaveBeenCalled();
      expect(ports.refreshPrices).toHaveBeenCalledOnce();
    });

    it('should refresh chains following the user default for blockchain', async () => {
      const ports = createPorts({ redetectByDefault: () => true });
      await createBalanceRefresher(ports).refreshSource(RefreshSource.BLOCKCHAIN);

      expect(ports.detectTokens).toHaveBeenCalledExactlyOnceWith(['eth']);
      expect(ports.queryChains).toHaveBeenCalledExactlyOnceWith(['btc']);
      expect(ports.queryExchanges).not.toHaveBeenCalled();
    });

    it('should only query chains when the caller opts out of redetection against the user default', async () => {
      const ports = createPorts({ redetectByDefault: () => true });
      await createBalanceRefresher(ports).refreshSource(RefreshSource.BLOCKCHAIN, { redetect: false });

      expect(ports.queryChains).toHaveBeenCalledExactlyOnceWith(['eth', 'btc']);
      expect(ports.detectTokens).not.toHaveBeenCalled();
    });

    it('should start pricing only after the source has settled', async () => {
      const banks = deferred();
      const ports = createPorts({ queryBanks: vi.fn<() => Promise<void>>(async () => banks.promise) });
      const running = createBalanceRefresher(ports).refreshSource(RefreshSource.BANKS);

      await vi.waitFor(() => expect(ports.queryBanks).toHaveBeenCalledOnce());
      await Promise.resolve();
      expect(ports.refreshPrices).not.toHaveBeenCalled();

      banks.resolve();
      await running;
      expect(ports.refreshPrices).toHaveBeenCalledOnce();
    });

    it('should still price and name the source when it fails', async () => {
      const ports = createPorts({ queryExchanges: async () => Promise.reject(new Error('exchange down')) });
      const outcome = await createBalanceRefresher(ports).refreshSource(RefreshSource.EXCHANGES);

      expect(ports.refreshPrices).toHaveBeenCalledOnce();
      assert(!outcome.ok);
      expect(outcome.error.map(failure => failure.source)).toEqual([RefreshSource.EXCHANGES]);
    });
  });

  describe('refreshPrices', () => {
    it('should only refresh prices', async () => {
      const ports = createPorts();
      const outcome = await createBalanceRefresher(ports).refreshPrices();

      expect(outcome.ok).toBe(true);
      expect(ports.refreshPrices).toHaveBeenCalledOnce();
      expect(ports.queryChains).not.toHaveBeenCalled();
    });
  });
});
