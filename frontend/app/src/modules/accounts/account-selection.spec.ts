import type { AddressData, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { describe, expect, it } from 'vitest';
import { matchesAccountQuery, selectableAccounts } from '@/modules/accounts/account-selection';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { createAccount } from '@/modules/accounts/create-account';

const ADDRESS_A = '0x1111111111111111111111111111111111111111';
const ADDRESS_B = '0x2222222222222222222222222222222222222222';

function account(address: string, chain: string, tags?: string[]): BlockchainAccount<AddressData> {
  return createAccount({ address, label: null, tags: tags ?? null }, { chain, nativeAsset: '' });
}

function chainsOf(accounts: BlockchainAccount<AddressData>[]): string[] {
  return accounts.map(item => item.chain);
}

describe('selectableAccounts', () => {
  describe('narrowing by chain', () => {
    it('should offer every account when no chain is named', () => {
      const accounts = [account(ADDRESS_A, 'eth'), account(ADDRESS_B, 'optimism')];

      expect(selectableAccounts(accounts)).toHaveLength(2);
    });

    it('should offer only the accounts on a named chain', () => {
      const accounts = [account(ADDRESS_A, 'eth'), account(ADDRESS_B, 'optimism')];

      expect(chainsOf(selectableAccounts(accounts, { chains: ['eth'] }))).toEqual(['eth']);
    });

    /** An all-chains account belongs to every chain, so narrowing must not filter it out. */
    it('should keep an all-chains account whatever chain is named', () => {
      const accounts = [account(ADDRESS_A, 'ALL'), account(ADDRESS_B, 'optimism')];

      expect(chainsOf(selectableAccounts(accounts, { chains: ['eth'] }))).toEqual(['ALL']);
    });
  });

  describe('collapsing an address tracked on several chains', () => {
    it('should offer one entry per address when unique', () => {
      const accounts = [account(ADDRESS_A, 'eth'), account(ADDRESS_A, 'optimism'), account(ADDRESS_B, 'eth')];

      const offered = selectableAccounts(accounts, { unique: true });

      expect(offered).toHaveLength(2);
      expect(offered.map(getAccountAddress)).toEqual([ADDRESS_A, ADDRESS_B]);
    });

    it('should offer every entry when not unique', () => {
      const accounts = [account(ADDRESS_A, 'eth'), account(ADDRESS_A, 'optimism')];

      expect(selectableAccounts(accounts)).toHaveLength(2);
    });
  });

  describe('the extra all-chains entry', () => {
    it('should add one for an address tracked on more than one chain', () => {
      const accounts = [account(ADDRESS_A, 'eth'), account(ADDRESS_A, 'optimism')];

      const offered = selectableAccounts(accounts, { multichain: true });

      expect(chainsOf(offered)).toEqual(['eth', 'optimism', 'ALL']);
      expect(getAccountAddress(offered[2])).toBe(ADDRESS_A);
    });

    it('should not add one for an address tracked on a single chain', () => {
      const accounts = [account(ADDRESS_A, 'eth'), account(ADDRESS_B, 'optimism')];

      expect(chainsOf(selectableAccounts(accounts, { multichain: true }))).toEqual(['eth', 'optimism']);
    });

    it('should add none when not asked for', () => {
      const accounts = [account(ADDRESS_A, 'eth'), account(ADDRESS_A, 'optimism')];

      expect(chainsOf(selectableAccounts(accounts))).toEqual(['eth', 'optimism']);
    });

    it('should add one per multi-chain address', () => {
      const accounts = [
        account(ADDRESS_A, 'eth'),
        account(ADDRESS_A, 'optimism'),
        account(ADDRESS_B, 'eth'),
        account(ADDRESS_B, 'base'),
      ];

      expect(chainsOf(selectableAccounts(accounts, { multichain: true }))).toEqual([
        'eth',
        'optimism',
        'eth',
        'base',
        'ALL',
        'ALL',
      ]);
    });
  });

  /**
   * The extra entries are synthesized rather than tracked, so appending them to the array the
   * caller passed would grow the list again on every pass.
   */
  describe('leaving the given accounts alone', () => {
    it('should not append the extra entries to the array it was given', () => {
      const accounts = [account(ADDRESS_A, 'eth'), account(ADDRESS_A, 'optimism')];

      selectableAccounts(accounts, { multichain: true });

      expect(accounts).toHaveLength(2);
    });

    it('should offer the same list however often it is called', () => {
      const accounts = [account(ADDRESS_A, 'eth'), account(ADDRESS_A, 'optimism')];

      const first = selectableAccounts(accounts, { multichain: true });
      const second = selectableAccounts(accounts, { multichain: true });

      expect(second).toHaveLength(first.length);
    });
  });
});

describe('matchesAccountQuery', () => {
  const noName = (): undefined => undefined;

  it('should match on the address', () => {
    expect(matchesAccountQuery(account(ADDRESS_A, 'eth'), ADDRESS_A, noName)).toBe(true);
  });

  it('should match on part of the address', () => {
    expect(matchesAccountQuery(account(ADDRESS_A, 'eth'), '1111', noName)).toBe(true);
  });

  it('should match on the resolved name', () => {
    expect(matchesAccountQuery(account(ADDRESS_A, 'eth'), 'alice', () => 'Alice ETH')).toBe(true);
  });

  it('should match a name whatever its case and spacing', () => {
    expect(matchesAccountQuery(account(ADDRESS_A, 'eth'), 'ALICE ETH', () => 'alice eth')).toBe(true);
  });

  it('should match on a tag', () => {
    expect(matchesAccountQuery(account(ADDRESS_A, 'eth', ['cold storage']), 'cold', noName)).toBe(true);
  });

  it('should not match an unrelated query', () => {
    expect(matchesAccountQuery(account(ADDRESS_A, 'eth', ['cold']), 'zzz', noName)).toBe(false);
  });

  it('should not match on a tag another account carries', () => {
    expect(matchesAccountQuery(account(ADDRESS_A, 'eth'), 'cold', noName)).toBe(false);
  });

  it('should match everything on an empty query', () => {
    expect(matchesAccountQuery(account(ADDRESS_A, 'eth'), '', noName)).toBe(true);
  });
});
