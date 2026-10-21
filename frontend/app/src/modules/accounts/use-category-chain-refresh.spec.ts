import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useCategoryChainRefresh } from '@/modules/accounts/use-category-chain-refresh';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';

const { chainIds, excluded } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    chainIds: ref<string[]>([]),
    excluded: ref<string[]>([]),
  };
});

vi.mock('@/modules/accounts/use-account-category-helper', () => ({
  useAccountCategoryHelper: (): object => ({ chainIds }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChainName: (chain: string): string => `name:${chain}` }),
}));

/** `excluded` holds a chain to exclude it whole, or `chain:address` to exclude one address on it. */
vi.mock('@/modules/settings/general/disabled-chain-queries/use-disabled-chains', () => ({
  useDisabledChains: (): object => ({
    isAddressExcluded: (chain: string, address: string): boolean =>
      get(excluded).includes(chain) || get(excluded).includes(`${chain}:${address}`),
  }),
}));

function track(...chains: string[]): void {
  const store = useBlockchainAccountsStore();
  for (const chain of chains)
    store.updateAccounts(chain, [createAccount({ address: '0x1', label: null, tags: null }, chain)]);
}

describe('useCategoryChainRefresh', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(chainIds, ['eth', 'optimism', 'gnosis', 'base']);
    set(excluded, []);
  });

  it('should list only the category chains that hold accounts', () => {
    track('eth', 'gnosis', 'btc');

    const { chains } = useCategoryChainRefresh('evm');

    expect(get(chains).map(state => state.chain)).toStrictEqual(['eth', 'gnosis']);
  });

  it('should order the chains from the oldest refresh to the newest', () => {
    track('eth', 'optimism', 'gnosis');
    useBlockchainRefreshTimestampsStore().updateTimestamps({ eth: 300, gnosis: 100, optimism: 200 });

    const { chains, oldest } = useCategoryChainRefresh('evm');

    expect(get(chains).map(state => state.chain)).toStrictEqual(['gnosis', 'optimism', 'eth']);
    expect(get(oldest)).toStrictEqual({ chain: 'gnosis', name: 'name:gnosis', skipped: false, timestamp: 100 });
  });

  it('should put a chain that was never refreshed first', () => {
    track('eth', 'base');
    useBlockchainRefreshTimestampsStore().updateTimestamps({ eth: 100 });

    const { oldest } = useCategoryChainRefresh('evm');

    expect(get(oldest)?.chain).toBe('base');
    expect(get(oldest)?.timestamp).toBeUndefined();
  });

  it('should keep a skipped chain last and out of the refreshable chains', () => {
    set(chainIds, ['gnosis', 'eth']);
    track('eth', 'gnosis');
    set(excluded, ['gnosis']);
    useBlockchainRefreshTimestampsStore().updateTimestamps({ eth: 300, gnosis: 100 });

    const { chains, oldest, refreshable } = useCategoryChainRefresh('evm');

    expect(get(chains).map(state => [state.chain, state.skipped])).toStrictEqual([['eth', false], ['gnosis', true]]);
    expect(get(refreshable).map(state => state.chain)).toStrictEqual(['eth']);
    expect(get(oldest)?.chain).toBe('eth');
  });

  it('should skip a chain whose every tracked address is excluded', () => {
    track('eth');
    set(excluded, ['eth:0x1']);

    const { chains } = useCategoryChainRefresh('evm');

    expect(get(chains).map(state => state.skipped)).toStrictEqual([true]);
  });

  it('should keep a chain refreshable while one of its addresses is still queried', () => {
    useBlockchainAccountsStore().updateAccounts('eth', [
      createAccount({ address: '0x1', label: null, tags: null }, 'eth'),
      createAccount({ address: '0x2', label: null, tags: null }, 'eth'),
    ]);
    set(excluded, ['eth:0x1']);

    const { refreshable } = useCategoryChainRefresh('evm');

    expect(get(refreshable).map(state => state.chain)).toStrictEqual(['eth']);
  });

  it('should have no oldest chain when every chain is skipped', () => {
    track('eth');
    set(excluded, ['eth']);

    const { oldest } = useCategoryChainRefresh('evm');

    expect(get(oldest)).toBeUndefined();
  });
});
