import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainAccountsStore } from './use-blockchain-accounts-store';

vi.mock('@/modules/accounts/account-utils', () => ({
  getAccountAddress: (account: { data: { address: string } }): string => account.data.address,
}));

function account(address: string, tags: string[] = [], label = ''): BlockchainAccount {
  return { chain: 'eth', data: { address, type: 'address' }, label, nativeAsset: 'ETH', tags };
}

describe('useBlockchainAccountsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should store and read accounts per chain', () => {
    const store = useBlockchainAccountsStore();
    store.updateAccounts('eth', [account('0x1')]);
    expect(store.getAccounts('eth')).toHaveLength(1);
    expect(store.getAccounts('missing')).toEqual([]);
  });

  it('should update the label and tags of the matching address', () => {
    const store = useBlockchainAccountsStore();
    store.updateAccounts('eth', [account('0x1'), account('0x2')]);
    store.updateAccountData({ address: '0x1', label: 'Renamed', tags: ['vip'] });
    const updated = store.getAccountByAddress('0x1', 'eth');
    expect(updated?.label).toBe('Renamed');
    expect(updated?.tags).toEqual(['vip']);
    expect(store.getAccountByAddress('0x2', 'eth')?.label).toBe('');
  });

  it('should find an account by address with or without a chain hint', () => {
    const store = useBlockchainAccountsStore();
    store.updateAccounts('eth', [account('0x1')]);
    store.updateAccounts('gnosis', [account('0x2')]);
    expect(store.getAccountByAddress('0x2')).toBeDefined();
    expect(store.getAccountByAddress('0x1', 'eth')).toBeDefined();
    expect(store.getAccountByAddress('0x9')).toBeUndefined();
  });

  it('should remove a tag across all chains', () => {
    const store = useBlockchainAccountsStore();
    store.updateAccounts('eth', [account('0x1', ['keep', 'drop'])]);
    store.removeTag('drop');
    expect(store.getAccountByAddress('0x1', 'eth')?.tags).toEqual(['keep']);
  });

  it('should rename a tag across all chains', () => {
    const store = useBlockchainAccountsStore();
    store.updateAccounts('eth', [account('0x1', ['old'])]);
    store.renameTag('old', 'new');
    expect(store.getAccountByAddress('0x1', 'eth')?.tags).toEqual(['new']);
  });

  it('should track added addresses and forget them after the ttl', () => {
    const store = useBlockchainAccountsStore();
    store.trackAddedAddresses(['0xabc'], 1000);
    expect(get(store.recentlyAddedAddresses).has('0xabc')).toBe(true);

    vi.advanceTimersByTime(1000);
    expect(get(store.recentlyAddedAddresses).has('0xabc')).toBe(false);
  });
});
