import type { TaskResult } from '@/modules/core/tasks/use-task-handler';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const h = vi.hoisted(() => ({
  detectEvmAccounts: vi.fn(),
  fetch: vi.fn(),
  fetchBlockchainBalances: vi.fn(),
  fetchEnsNames: vi.fn(),
  getAddresses: vi.fn((_chain: string): string[] => []),
  isEvm: vi.fn((chain: string): boolean => chain === 'eth' || chain === 'optimism'),
  notifyError: vi.fn(),
  refreshBlockchainBalances: vi.fn(),
  resetStatus: vi.fn(),
  runTask: vi.fn(),
  supportsTransactions: vi.fn((): boolean => true),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts', () => ({
  useBlockchainAccounts: vi.fn(() => ({ fetch: h.fetch })),
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
      supportedChains: vue.ref([{ id: 'eth' }, { id: 'btc' }]),
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

vi.mock('@/modules/shell/sync-progress/use-status-updater', () => ({
  useStatusUpdater: vi.fn(() => ({ resetStatus: h.resetStatus })),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/core/tasks/use-task-handler')>();
  return { ...actual, useTaskHandler: vi.fn(() => ({ runTask: h.runTask })) };
});

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

function actionable(message: string): TaskResult<never> {
  return { backendCancelled: false, cancelled: false, error: new Error(message), message, skipped: false, success: false };
}

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
  });

  describe('resetStatuses', () => {
    it('should reset the nft section status', async () => {
      const { useAccountOperations } = await importModule();
      useAccountOperations().resetStatuses();
      expect(h.resetStatus).toHaveBeenCalledOnce();
    });
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
      h.runTask.mockResolvedValue(actionable('detect failed'));
      const { useAccountOperations } = await importModule();
      await useAccountOperations().detectEvmAccounts();
      expect(h.notifyError).toHaveBeenCalledOnce();
    });

    it('should not notify on success', async () => {
      h.runTask.mockResolvedValue({ result: undefined, success: true });
      const { useAccountOperations } = await importModule();
      await useAccountOperations().detectEvmAccounts();
      expect(h.notifyError).not.toHaveBeenCalled();
    });
  });
});
