import type { MigratedAddresses } from '@/modules/core/messaging/types';
import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import '@test/i18n';

const h = vi.hoisted(() => ({
  fetchAccounts: vi.fn(),
  isEvm: vi.fn((chain: string): boolean => chain === 'eth' || chain === 'optimism'),
  notify: vi.fn(),
  refreshBlockchainBalances: vi.fn(),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const vue = await import('vue');
  return {
    useSupportedChains: vi.fn(() => ({
      evmAndEvmLikeTxChainsInfo: vue.ref([{ id: 'eth' }, { id: 'optimism' }, { id: 'zksync_lite' }]),
      getChainName: (chain: string): string => chain,
      isEvm: h.isEvm,
    })),
  };
});

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn(() => ({ fetchAccounts: h.fetchAccounts })),
}));

vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn(() => ({ refreshBlockchainBalances: h.refreshBlockchainBalances })),
}));

vi.mock('@/modules/auth/use-logged-user-identifier', async () => {
  const vue = await import('vue');
  return { useLoggedUserIdentifier: vi.fn(() => vue.ref(null)) };
});

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notify: h.notify })),
}));

async function importModule(): Promise<typeof import('./use-account-migration')> {
  return import('./use-account-migration');
}

describe('useAccountMigration', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    h.fetchAccounts.mockResolvedValue(undefined);
    h.refreshBlockchainBalances.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should migrate an evm address once data can be requested', async () => {
    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, true);
    const migrated: MigratedAddresses = [{ address: '0xabc', chain: 'eth' }];

    const { useAccountMigration } = await importModule();
    useAccountMigration().setUpgradedAddresses(migrated);

    expect(h.fetchAccounts).toHaveBeenCalledWith({ blockchain: 'eth' });
    expect(h.notify).toHaveBeenCalledOnce();
    await flushPromises();
    expect(h.refreshBlockchainBalances).toHaveBeenCalledWith(
      { blockchain: 'eth' },
      'background',
      { detect: true, detectAddresses: ['0xabc'] },
    );
  });

  it('should defer migration until data can be requested', async () => {
    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, false);
    const { useAccountMigration } = await importModule();
    useAccountMigration().setUpgradedAddresses([{ address: '0xabc', chain: 'eth' }]);
    expect(h.fetchAccounts).not.toHaveBeenCalled();

    set(canRequestData, true);
    await nextTick();
    expect(h.fetchAccounts).toHaveBeenCalledWith({ blockchain: 'eth' });
  });

  it('should ignore addresses on chains without token detection', async () => {
    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, true);
    const { useAccountMigration } = await importModule();
    useAccountMigration().setUpgradedAddresses([{ address: 'bc1abc', chain: 'btc' }]);
    expect(h.fetchAccounts).not.toHaveBeenCalled();
    expect(h.notify).not.toHaveBeenCalled();
  });

  /**
   * `isEvm` gates *detection*, never the query. `tokenChains` is built from
   * `evmAndEvmLikeTxChainsInfo`, so an evm-like chain reaches the loop with `isEvm` false; gating
   * the query on it too would leave a migrated zksync_lite address with no balances at all, because
   * the cache-only read cannot fetch what was never queried.
   */
  it('should still query balances for evmlike chains, without detecting', async () => {
    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, true);
    const { useAccountMigration } = await importModule();
    useAccountMigration().setUpgradedAddresses([{ address: '0xdef', chain: 'zksync_lite' }]);
    await flushPromises();
    expect(h.fetchAccounts).toHaveBeenCalledWith({ blockchain: 'zksync_lite' });
    expect(h.refreshBlockchainBalances).toHaveBeenCalledWith(
      { blockchain: 'zksync_lite' },
      'background',
      {},
    );
  });

  /**
   * The job's `shouldQuery` reads the accounts store, so a job that starts before the accounts
   * land sees none, clears the chain and settles SKIPPED. Ordering, not concurrency.
   */
  it('should read the accounts before querying the chain', async () => {
    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, true);
    const { useAccountMigration } = await importModule();
    useAccountMigration().setUpgradedAddresses([{ address: '0xabc', chain: 'eth' }]);
    await flushPromises();
    expect(h.fetchAccounts.mock.invocationCallOrder[0])
      .toBeLessThan(h.refreshBlockchainBalances.mock.invocationCallOrder[0]);
  });

  it('should wait for the accounts read to settle, not merely start it first', async () => {
    let landed = (): void => {};
    h.fetchAccounts.mockImplementation(async () => new Promise<void>((resolve) => {
      landed = resolve;
    }));

    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, true);
    const { useAccountMigration } = await importModule();
    useAccountMigration().setUpgradedAddresses([{ address: '0xabc', chain: 'eth' }]);
    await flushPromises();

    expect(h.refreshBlockchainBalances).not.toHaveBeenCalled();

    landed();
    await flushPromises();

    expect(h.refreshBlockchainBalances).toHaveBeenCalledOnce();
  });
});
