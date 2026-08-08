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
  fetchBlockchainBalances: vi.fn(),
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
    fetchBlockchainBalances: h.fetchBlockchainBalances,
    refreshBlockchainBalances: h.refreshBlockchainBalances,
  })),
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
    h.fetchBlockchainBalances.mockResolvedValue(undefined);
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
      await useAccountOperations().fetchAccounts('eth', true);
      expect(h.fetch).toHaveBeenCalledWith('eth');
      await flushPromises();
      expect(h.fetchEnsNames).toHaveBeenCalledWith([{ address: '0xabc', blockchain: 'eth' }], true);
    });

    it('should not resolve ens names for non-evm chains', async () => {
      h.getAddresses.mockReturnValue(['bc1abc']);
      const { useAccountOperations } = await importModule();
      await useAccountOperations().fetchAccounts('btc');
      expect(h.fetch).toHaveBeenCalledWith('btc');
      expect(h.fetchEnsNames).not.toHaveBeenCalled();
    });

    /**
     * 🔴 eth2 is not an accounts read — it is a backend task that re-queries validators, and the
     * slowest leg of the walk. Inside the tracked `Promise.all` it gated everything downstream:
     * observed after a re-login as all 17 chains' accounts landing and not one balance being
     * fetched, because the walk never resolved.
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
      // Still read, just not waited on.
      expect(h.fetch).toHaveBeenCalledWith('eth2');
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
      expect(h.fetchBlockchainBalances).toHaveBeenCalledWith({ addresses: undefined, blockchain: 'eth', isXpub: false });
      expect(h.refreshBlockchainBalances).not.toHaveBeenCalled();
    });

    it('should refresh balances for the eth2 chain', async () => {
      const { useAccountOperations } = await importModule();
      await useAccountOperations().refreshAccounts({ blockchain: 'eth2' });
      expect(h.refreshBlockchainBalances).toHaveBeenCalledWith({ addresses: undefined, blockchain: 'eth2', isXpub: false }, false);
    });

    it('should pass unique addresses for a chain without transaction support', async () => {
      h.supportsTransactions.mockReturnValue(false);
      const { useAccountOperations } = await importModule();
      await useAccountOperations().refreshAccounts({ addresses: ['0xa', '0xa', '0xb'], blockchain: 'gnosis', isXpub: true });
      expect(h.refreshBlockchainBalances).toHaveBeenCalledWith({ addresses: ['0xa', '0xb'], blockchain: 'gnosis', isXpub: true }, false);
    });

    it('should schedule an eth2 refresh when eth has validators', async () => {
      h.getAddresses.mockImplementation((chain: string): string[] => (chain === 'eth2' ? ['0xval'] : []));
      const { useAccountOperations } = await importModule();
      await useAccountOperations().refreshAccounts({ blockchain: 'eth' });
      await flushPromises();
      expect(h.refreshBlockchainBalances).toHaveBeenCalledWith({ addresses: undefined, blockchain: 'eth2', isXpub: false }, false);
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
