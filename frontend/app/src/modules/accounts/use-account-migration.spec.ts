import type { MigratedAddresses } from '@/modules/core/messaging/types';
import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import '@test/i18n';

const h = vi.hoisted(() => ({
  detectTokens: vi.fn(),
  fetchAccounts: vi.fn(),
  isEvm: vi.fn((chain: string): boolean => chain === 'eth' || chain === 'optimism'),
  notify: vi.fn(),
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

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: vi.fn(() => ({ detectTokens: h.detectTokens })),
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
    h.detectTokens.mockResolvedValue(undefined);
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
    expect(h.detectTokens).toHaveBeenCalledWith('eth', ['0xabc']);
    expect(h.notify).toHaveBeenCalledOnce();
    await flushPromises();
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

  it('should fetch accounts but skip token detection for evmlike chains', async () => {
    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, true);
    const { useAccountMigration } = await importModule();
    useAccountMigration().setUpgradedAddresses([{ address: '0xdef', chain: 'zksync_lite' }]);
    expect(h.fetchAccounts).toHaveBeenCalledWith({ blockchain: 'zksync_lite' });
    expect(h.detectTokens).not.toHaveBeenCalled();
  });
});
