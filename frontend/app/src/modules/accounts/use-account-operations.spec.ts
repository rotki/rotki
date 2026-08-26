import { runSpecWith } from '@test/utils/mocks/native-task';
import { flushPromises } from '@vue/test-utils';
import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const h = vi.hoisted(() => ({
  // Mutable so a test can add a chain (eth2) without a second module mock.
  chainIds: ['eth', 'btc'],
  detectEvmAccounts: vi.fn(),
  fetch: vi.fn(),
  hydrate: vi.fn(),
  fetchEnsNames: vi.fn(),
  getAddresses: vi.fn((_chain: string): string[] => []),
  isEvm: vi.fn((chain: string): boolean => chain === 'eth' || chain === 'optimism'),
  notifyError: vi.fn(),
  refreshBlockchainBalances: vi.fn(),
  runTaskResult: vi.fn(),
  supportsTransactions: vi.fn((): boolean => true),
}));

const submitTask = vi.fn(runSpecWith(h.runTaskResult));

vi.mock('@/modules/accounts/use-account-fetching', () => ({
  useAccountFetching: vi.fn(() => ({ fetch: h.fetch })),
}));

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn(() => ({
    refreshBlockchainBalances: h.refreshBlockchainBalances,
  })),
}));

vi.mock('@/modules/balances/use-balance-hydration', () => ({
  useBalanceHydration: vi.fn(() => ({ hydrate: h.hydrate })),
}));

vi.mock('@/modules/accounts/address-book/use-ens-operations', () => ({
  useEnsOperations: vi.fn(() => ({ fetchEnsNames: h.fetchEnsNames })),
}));

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({ detectEvmAccounts: h.detectEvmAccounts })),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const vue = await import('vue');
  return {
    useSupportedChains: vi.fn(() => ({
      isEvm: h.isEvm,
      supportedChains: vue.computed(() => h.chainIds.map(id => ({ id }))),
      supportsTransactions: h.supportsTransactions,
    })),
  };
});

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: vi.fn(() => ({ getAddresses: h.getAddresses })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: h.notifyError })),
}));

vi.mock('@/modules/task-center/use-native-task', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNativeTask: vi.fn(() => ({ cancelByType: vi.fn(() => vi.fn()), runTaskResult: h.runTaskResult, statusOf: vi.fn(), submitTask })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

async function importModule(): Promise<typeof import('./use-account-operations')> {
  return import('./use-account-operations');
}

describe('useAccountOperations', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    h.getAddresses.mockReturnValue([]);
    h.supportsTransactions.mockReturnValue(true);
    h.fetch.mockResolvedValue(undefined);
    h.hydrate.mockResolvedValue(undefined);
    h.refreshBlockchainBalances.mockResolvedValue(undefined);
    h.fetchEnsNames.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
    h.chainIds = ['eth', 'btc'];
  });

  describe('fetchAccounts', () => {
    it('should fetch the given chain and resolve ens names for evm chains', async () => {
      h.getAddresses.mockReturnValue(['0xabc']);
      const { useAccountOperations } = await importModule();
      await useAccountOperations().fetchAccounts({ blockchain: 'eth', refreshEns: true });
      expect(h.fetch).toHaveBeenCalledWith('eth');
      await flushPromises();
      expect(h.fetchEnsNames).toHaveBeenCalledWith([{ address: '0xabc', blockchain: 'eth' }], true);
    });

    it('should not resolve ens names for non-evm chains', async () => {
      h.getAddresses.mockReturnValue(['bc1abc']);
      const { useAccountOperations } = await importModule();
      await useAccountOperations().fetchAccounts({ blockchain: 'btc' });
      expect(h.fetch).toHaveBeenCalledWith('btc');
      expect(h.fetchEnsNames).not.toHaveBeenCalled();
    });

    /**
     * eth2 is not an accounts read but a backend task re-querying validators, and the slowest leg
     * of the walk. Awaited with the rest it gates every chain's balances behind itself.
     */
    it('should not hold the full walk on eth2', async () => {
      h.chainIds = ['eth', 'btc', 'eth2'];
      h.fetch.mockImplementation(async (chain: string) => {
        if (chain === 'eth2')
          return new Promise<void>(() => {});

        return undefined;
      });

      const { useAccountOperations } = await importModule();
      const walk = await Promise.race([
        useAccountOperations().fetchAccounts().then(() => 'resolved'),
        new Promise<string>((resolve) => {
          setTimeout(resolve, 50, 'HUNG');
        }),
      ]);

      expect(walk).toBe('resolved');
      expect(h.fetch).toHaveBeenCalledWith('eth2');
    });

    /**
     * `allWithConcurrency` short-circuits on the first `err`, so the third chain is load-bearing:
     * with a bound of 2 and eth rejecting, optimism is the one that would silently never be read.
     * The naive version passes every other test in this file.
     */
    it('should read every chain even when one read rejects', async () => {
      h.chainIds = ['eth', 'btc', 'optimism'];
      h.fetch.mockImplementation(async (chain: string) => {
        if (chain === 'eth')
          throw new Error('boom');

        return undefined;
      });

      const { useAccountOperations } = await importModule();
      await useAccountOperations().fetchAccounts();
      await flushPromises();

      expect(h.fetch).toHaveBeenCalledWith('btc');
      expect(h.fetch).toHaveBeenCalledWith('optimism');
      expect(h.hydrate).toHaveBeenCalledWith({ blockchain: 'optimism' });
    });

    it('should read a chain\'s cached balances as that chain lands, not after the walk', async () => {
      h.chainIds = ['eth', 'btc'];
      let releaseBtc = (): void => {};
      h.fetch.mockImplementation(async (chain: string) => {
        if (chain === 'btc') {
          return new Promise<void>((resolve): void => {
            releaseBtc = resolve;
          });
        }

        return undefined;
      });

      const { useAccountOperations } = await importModule();
      const walk = useAccountOperations().fetchAccounts();
      await vi.waitFor(() => {
        expect(h.hydrate).toHaveBeenCalledWith(expect.objectContaining({ blockchain: 'eth' }));
      });

      expect(h.hydrate).not.toHaveBeenCalledWith(expect.objectContaining({ blockchain: 'btc' }));

      releaseBtc();
      await walk;
    });

    it('should not sweep every chain again after the walk', async () => {
      const { useAccountOperations } = await importModule();
      await useAccountOperations().fetchAccounts({ refreshEns: true });
      await flushPromises();

      const undirectedSweep = expect.objectContaining({ blockchain: undefined });
      expect(h.hydrate).toHaveBeenCalledWith(expect.objectContaining({ blockchain: 'eth' }));
      expect(h.hydrate).toHaveBeenCalledWith(expect.objectContaining({ blockchain: 'btc' }));
      expect(h.hydrate).not.toHaveBeenCalledWith(undirectedSweep);
    });

    it('should fall back to every supported chain when no chain is given', async () => {
      const { useAccountOperations } = await importModule();
      await useAccountOperations().fetchAccounts();
      expect(h.fetch).toHaveBeenCalledWith('eth');
      expect(h.fetch).toHaveBeenCalledWith('btc');
    });
  });

  describe('refreshAccounts', () => {
    it('should fetch balances for a regular chain', async () => {
      const { useAccountOperations } = await importModule();
      await useAccountOperations().refreshAccounts({ blockchain: 'eth' });
      expect(h.hydrate).toHaveBeenCalledWith({ addresses: undefined, blockchain: 'eth', isXpub: false });
      expect(h.refreshBlockchainBalances).not.toHaveBeenCalled();
    });

    it('should refresh balances for the eth2 chain', async () => {
      const { useAccountOperations } = await importModule();
      await useAccountOperations().refreshAccounts({ blockchain: 'eth2' });
      expect(h.refreshBlockchainBalances).toHaveBeenCalledWith({ addresses: undefined, blockchain: 'eth2', isXpub: false }, 'background');
    });

    it('should pass unique addresses for a chain without transaction support', async () => {
      h.supportsTransactions.mockReturnValue(false);
      const { useAccountOperations } = await importModule();
      await useAccountOperations().refreshAccounts({ addresses: ['0xa', '0xa', '0xb'], blockchain: 'gnosis', isXpub: true });
      expect(h.refreshBlockchainBalances).toHaveBeenCalledWith({ addresses: ['0xa', '0xb'], blockchain: 'gnosis', isXpub: true }, 'background');
    });

    it('should schedule an eth2 refresh when eth has validators', async () => {
      h.getAddresses.mockImplementation((chain: string): string[] => (chain === 'eth2' ? ['0xval'] : []));
      const { useAccountOperations } = await importModule();
      await useAccountOperations().refreshAccounts({ blockchain: 'eth' });
      await flushPromises();
      expect(h.refreshBlockchainBalances).toHaveBeenCalledWith({ addresses: undefined, blockchain: 'eth2', isXpub: false }, 'background');
    });
  });

  describe('detectEvmAccounts', () => {
    it('should notify on an actionable failure', async () => {
      h.runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'detect failed' })));
      const { useAccountOperations } = await importModule();
      await useAccountOperations().detectEvmAccounts();
      expect(h.notifyError).toHaveBeenCalledOnce();
    });

    it('should not notify on success', async () => {
      h.runTaskResult.mockResolvedValue(ok(undefined));
      const { useAccountOperations } = await importModule();
      await useAccountOperations().detectEvmAccounts();
      expect(h.notifyError).not.toHaveBeenCalled();
    });
  });
});
