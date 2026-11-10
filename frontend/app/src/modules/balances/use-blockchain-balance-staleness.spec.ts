import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { AccountKind } from '@/modules/accounts/blockchain-accounts';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainBalanceStaleness } from '@/modules/balances/use-blockchain-balance-staleness';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';

const rules = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    disabledChains: ref<string[]>([]),
    excludedAddresses: ref<string[]>([]),
  };
});

vi.mock('@/modules/settings/general/disabled-chain-queries/use-disabled-chains', () => ({
  useDisabledChains: (): {
    isAddressExcluded: (chain: string, address: string) => boolean;
    isChainExcluded: (chain: string) => boolean;
    isEveryAddressExcluded: (chain: string, addresses: string[]) => boolean;
  } => ({
    isAddressExcluded: (_chain: string, address: string): boolean => rules.excludedAddresses.value.includes(address),
    isChainExcluded: (chain: string): boolean => rules.disabledChains.value.includes(chain),
    isEveryAddressExcluded: (_chain: string, addresses: string[]): boolean =>
      addresses.length > 0 && addresses.every(address => rules.excludedAddresses.value.includes(address)),
  }),
}));

describe('useBlockchainBalanceStaleness', () => {
  let store: ReturnType<typeof useBlockchainRefreshTimestampsStore>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useBlockchainRefreshTimestampsStore();
    vi.useFakeTimers();
    rules.disabledChains.value = [];
    rules.excludedAddresses.value = [];
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should return undefined timestamp when no data exists', () => {
    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBeUndefined();
  });

  it('should return the oldest timestamp across all chains', () => {
    const now = Math.floor(Date.now() / 1000);
    store.updateTimestamps({ eth: now - 300, btc: now - 100 });

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBe(now - 300);
  });

  it('should return timestamp for a specific chain when provided', () => {
    const now = Math.floor(Date.now() / 1000);
    store.updateTimestamps({ eth: now - 300, btc: now - 100 });

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness('btc');
    expect(get(lastRefreshTimestamp)).toBe(now - 100);
  });

  it('should return undefined for a specific chain with no data', () => {
    store.updateTimestamps({ eth: 1000 });

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness('btc');
    expect(get(lastRefreshTimestamp)).toBeUndefined();
  });

  it('should support reactive chain parameter', () => {
    const now = Math.floor(Date.now() / 1000);
    store.updateTimestamps({ eth: now - 300, btc: now - 100 });

    const chain = ref<string | undefined>('eth');
    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness(chain);
    expect(get(lastRefreshTimestamp)).toBe(now - 300);

    set(chain, 'btc');
    expect(get(lastRefreshTimestamp)).toBe(now - 100);

    set(chain, undefined);
    // When no chain specified, returns the oldest
    expect(get(lastRefreshTimestamp)).toBe(now - 300);
  });

  it('should ignore a disabled chain in the oldest timestamp', () => {
    store.updateTimestamps({ eth: 100, gnosis: 50 });
    rules.disabledChains.value = ['gnosis'];

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBe(100);
  });

  it('should return undefined when every chain is disabled', () => {
    store.updateTimestamps({ eth: 100, gnosis: 50 });
    rules.disabledChains.value = ['eth', 'gnosis'];

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBeUndefined();
  });

  it('should ignore a chain whose tracked addresses all become excluded while running', () => {
    useBlockchainAccountsStore().updateAccounts('gnosis', [
      { kind: AccountKind.ADDRESS, address: '0xA', chain: 'gnosis' },
    ]);
    store.updateTimestamps({ eth: 100, gnosis: 50 });

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBe(50);

    rules.excludedAddresses.value = ['0xA'];
    expect(get(lastRefreshTimestamp)).toBe(100);
  });

  it('should keep a chain that still has an enabled tracked address', () => {
    useBlockchainAccountsStore().updateAccounts('gnosis', [
      { kind: AccountKind.ADDRESS, address: '0xA', chain: 'gnosis' },
      { kind: AccountKind.ADDRESS, address: '0xB', chain: 'gnosis' },
    ]);
    store.updateTimestamps({ eth: 100, gnosis: 50 });
    rules.excludedAddresses.value = ['0xA'];

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBe(50);
  });

  it('should ignore a camelCased chain whose tracked addresses are all excluded', () => {
    useBlockchainAccountsStore().updateAccounts('polygon_pos', [
      { kind: AccountKind.ADDRESS, address: '0xA', chain: 'polygon_pos' },
    ]);
    store.updateTimestamps({ eth: 100, polygonPos: 50 });
    rules.excludedAddresses.value = ['0xA'];

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBe(100);
  });

  it('should ignore an xpub chain once every derived address is excluded', () => {
    useBlockchainAccountsStore().updateAccounts('btc', [
      { kind: AccountKind.XPUB, xpub: 'xpub123', chain: 'btc' },
      { kind: AccountKind.ADDRESS, address: '1A', chain: 'btc', xpubParent: { xpub: 'xpub123' } },
    ]);
    store.updateTimestamps({ btc: 50, eth: 100 });
    rules.excludedAddresses.value = ['1A'];

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBe(100);
  });
});
