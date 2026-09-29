import type {
  AddressAccount,
  AddressGroupWithBalance,
  BlockchainAccountBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
} from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it, vi } from 'vitest';
import { getAccountAddress, getAccountGroupId } from '@/modules/accounts/account-utils';
import { sortAndFilterAccounts } from './account-list';

type AddressRow = BlockchainAccountWithBalance<AddressAccount>;

function account(overrides: Partial<Omit<AddressRow, 'groupId'>> = {}): AddressRow {
  const row: Omit<AddressRow, 'groupId'> = {
    address: '0xabc',
    amount: bigNumberify(1),
    chain: 'eth',
    kind: 'address',
    type: 'account',
    value: bigNumberify(1000),
    ...overrides,
  };
  return { ...row, groupId: getAccountGroupId(row) };
}

function payload(overrides: Partial<BlockchainAccountRequestPayload> = {}): BlockchainAccountRequestPayload {
  return {
    limit: 10,
    offset: 0,
    ...overrides,
  };
}

type LabelResolver = (account: BlockchainAccountBalance, chain?: string) => string | undefined;

const noLabel = (): undefined => undefined;

describe('sortAndFilterAccounts', () => {
  const accounts = (): BlockchainAccountWithBalance[] => [
    account({ address: '0xaaa', chain: 'eth', label: 'Alpha', tags: ['hot'], value: bigNumberify(300) }),
    account({ address: '0xbbb', chain: 'optimism', label: 'Beta', tags: ['cold'], value: bigNumberify(100) }),
    account({ address: '0xccc', chain: 'eth', label: 'Gamma', tags: ['hot', 'cold'], value: bigNumberify(200) }),
  ];

  it('should return all accounts when no filter is applied', () => {
    const result = sortAndFilterAccounts(accounts(), payload(), { getLabel: noLabel });
    expect(result.data).toHaveLength(3);
    expect(result.found).toBe(3);
    expect(result.total).toBe(3);
    expect(result.totalValue?.toNumber()).toBe(600);
  });

  it('should filter by a picked address', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ addresses: ['0xbbb'] }), { getLabel: noLabel });
    expect(result.data.map(getAccountAddress)).toEqual(['0xbbb']);
  });

  it('should keep every account among several picked addresses, which are alternatives rather than requirements', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ addresses: ['0xaaa', '0xccc'] }), { getLabel: noLabel });
    expect(result.data.map(getAccountAddress)).toEqual(['0xaaa', '0xccc']);
  });

  it('should match a picked address regardless of case', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ addresses: ['0xBBB'] }), { getLabel: noLabel });
    expect(result.data.map(getAccountAddress)).toEqual(['0xbbb']);
  });

  it('should not match a picked address by fragment, which would silently widen what the user chose', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ addresses: ['0xbb'] }), { getLabel: noLabel });
    expect(result.data).toHaveLength(0);
  });

  it('should filter by chain', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ chain: ['eth'] }), { getLabel: noLabel });
    expect(result.data.map(getAccountAddress)).toEqual(['0xaaa', '0xccc']);
  });

  it('should filter by tags requiring every tag to match', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ tags: ['hot', 'cold'] }), { getLabel: noLabel });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].label).toBe('Gamma');
  });

  it('should sort ascending by value', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ ascending: [true], orderByAttributes: ['value'] }), { getLabel: noLabel });
    expect(result.data.map(a => a.value.toNumber())).toEqual([100, 200, 300]);
  });

  it('should sort descending by value', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ ascending: [false], orderByAttributes: ['value'] }), { getLabel: noLabel });
    expect(result.data.map(a => a.value.toNumber())).toEqual([300, 200, 100]);
  });

  it('should sort by label using the resolver', () => {
    const result = sortAndFilterAccounts(accounts(), payload({ ascending: [false], orderByAttributes: ['label'] }), { getLabel: noLabel });
    expect(result.data.map(a => a.label)).toEqual(['Gamma', 'Beta', 'Alpha']);
  });

  it('should sort by the resolved label ahead of the stored one', () => {
    const getLabel = (row: BlockchainAccountBalance): string | undefined => (getAccountAddress(row) === '0xaaa' ? 'Zulu' : undefined);
    const result = sortAndFilterAccounts(accounts(), payload({ ascending: [true], orderByAttributes: ['label'] }), { getLabel });
    expect(result.data.map(getAccountAddress)).toEqual(['0xbbb', '0xccc', '0xaaa']);
  });

  it('should sort an account whose label is unset by its address', () => {
    const rows = [
      account({ address: '0xccc', label: 'Beta' }),
      account({ address: '0xaaa', label: undefined }),
      account({ address: '0xbbb', label: 'Alpha' }),
    ];
    const result = sortAndFilterAccounts(rows, payload({ ascending: [true], orderByAttributes: ['label'] }), { getLabel: noLabel });
    expect(result.data.map(getAccountAddress)).toEqual(['0xaaa', '0xbbb', '0xccc']);
  });

  it('should break a tie on the first attribute with the next one', () => {
    const rows = [
      account({ address: '0xaaa', label: 'Gamma', value: bigNumberify(100) }),
      account({ address: '0xbbb', label: 'Alpha', value: bigNumberify(100) }),
      account({ address: '0xccc', label: 'Beta', value: bigNumberify(300) }),
    ];
    const result = sortAndFilterAccounts(rows, payload({
      ascending: [false, true],
      orderByAttributes: ['value', 'label'],
    }), { getLabel: noLabel });
    expect(result.data.map(getAccountAddress)).toEqual(['0xccc', '0xbbb', '0xaaa']);
  });

  it('should skip an attribute the rows do not have and sort by the next one', () => {
    const result = sortAndFilterAccounts(accounts(), payload({
      ascending: [true, true],
      orderByAttributes: ['included_value', 'value'],
    }), { getLabel: noLabel });
    expect(result.data.map(a => a.value.toNumber())).toEqual([100, 200, 300]);
  });

  it('should keep the input order of rows that tie on every attribute', () => {
    const rows = [
      account({ address: '0xccc', value: bigNumberify(100) }),
      account({ address: '0xaaa', value: bigNumberify(100) }),
      account({ address: '0xbbb', value: bigNumberify(100) }),
    ];
    const result = sortAndFilterAccounts(rows, payload({ ascending: [true], orderByAttributes: ['value'] }), { getLabel: noLabel });
    expect(result.data.map(getAccountAddress)).toEqual(['0xccc', '0xaaa', '0xbbb']);
  });

  it('should resolve each row\'s label once, not once per comparison', () => {
    const rows = Array.from({ length: 20 }, (_, i) => account({ address: `0x${i.toString().padStart(3, '0')}`, label: undefined }));
    const getLabel = vi.fn<LabelResolver>(() => undefined);
    sortAndFilterAccounts(rows, payload({ ascending: [true], orderByAttributes: ['label'] }), { getLabel });
    expect(getLabel).toHaveBeenCalledTimes(rows.length);
  });

  it('should not resolve labels when not sorting by label', () => {
    const getLabel = vi.fn<LabelResolver>(() => undefined);
    sortAndFilterAccounts(accounts(), payload({ ascending: [true], orderByAttributes: ['value'] }), { getLabel });
    expect(getLabel).not.toHaveBeenCalled();
  });

  it('should paginate using offset and limit', () => {
    const result = sortAndFilterAccounts(accounts(), payload({
      ascending: [true],
      limit: 1,
      offset: 1,
      orderByAttributes: ['value'],
    }), { getLabel: noLabel });
    expect(result.data).toHaveLength(1);
    expect(result.data[0].value.toNumber()).toBe(200);
    expect(result.found).toBe(3);
  });
});

/**
 * A group stands for its member accounts, so a filter that can match on different members, or an
 * exclusion that drops some of them, has to be resolved against the members rather than the group.
 */
describe('sortAndFilterAccounts, over groups', () => {
  function group(overrides: Partial<AddressGroupWithBalance> = {}): AddressGroupWithBalance {
    return {
      address: '0xaaa',
      category: 'evm',
      chains: ['eth', 'optimism'],
      kind: 'address',
      tags: ['hot'],
      type: 'group',
      value: bigNumberify(300),
      ...overrides,
    };
  }

  function member(chain: string, value: number, tags: string[]): BlockchainAccountWithBalance {
    return account({ address: '0xaaa', chain, tags, value: bigNumberify(value) });
  }

  const members = (): BlockchainAccountWithBalance[] => [
    member('eth', 200, ['hot']),
    member('optimism', 100, ['cold']),
  ];

  it('should keep only the groups of the picked category', () => {
    const bitcoin = group({ address: 'bc1qaaa', category: 'bitcoin', chains: ['btc'] });
    const result = sortAndFilterAccounts([group(), bitcoin], payload({ category: 'bitcoin' }), { getLabel: noLabel });

    expect(result.data).toEqual([bitcoin]);
  });

  /** The excluded chains are still part of the group, they just stop counting towards its value. */
  describe('an excluded chain', () => {
    it('should leave the group holding only what is still included', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ excluded: { '0xaaa': ['optimism'] } }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].includedValue?.toNumber()).toBe(200);
    });

    it('should leave a group with nothing excluded alone', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ excluded: { '0xbbb': ['optimism'] } }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].includedValue).toBeUndefined();
    });

    it('should still apply when only a filter that ignores members is active', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ addresses: ['0xaaa'], category: 'evm', excluded: { '0xaaa': ['optimism'] } }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].includedValue?.toNumber()).toBe(200);
      expect(result.data[0].value.toNumber()).toBe(300);
    });

    it('should apply to a group narrowed by a chain filter', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ chain: ['eth', 'optimism'], excluded: { '0xaaa': ['optimism'] } }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].includedValue?.toNumber()).toBe(200);
      expect(result.data[0].value.toNumber()).toBe(300);
    });

    it('should count every group in the total, excluded chains included', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ excluded: { '0xaaa': ['optimism'] } }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.totalValue?.toNumber()).toBe(300);
    });

    /** A group on one chain cannot have that chain excluded and still be a group worth showing. */
    it('should leave a single-chain group alone', () => {
      const result = sortAndFilterAccounts(
        [group({ chains: ['eth'] })],
        payload({ excluded: { '0xaaa': ['eth'] } }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].includedValue).toBeUndefined();
    });
  });

  /**
   * A tag or chain filter matching different members would otherwise show the whole group, which
   * says the group matched when no single account in it did.
   */
  describe('a filter that can match different members', () => {
    it('should narrow the group to the members that match the chain', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ chain: ['eth'] }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].chains).toEqual(['eth']);
      expect(result.data[0].value.toNumber()).toBe(200);
    });

    it('should keep the chains the group spans, so what was narrowed away is still known', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ chain: ['eth'] }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].allChains).toEqual(['eth', 'optimism']);
    });

    it('should carry only the tags of the members that survived', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ chain: ['optimism'] }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].tags).toEqual(['cold']);
    });

    /** One surviving member is no longer a group of alternatives, so it expands as that account. */
    it('should expand a single survivor as itself', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ chain: ['eth'] }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].expansion).toBeUndefined();
    });

    it('should expand several survivors as accounts', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ chain: ['eth', 'optimism'] }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].expansion).toBe('accounts');
    });

    /** Tag and chain have to hold on the same member, not on two different ones. */
    it('should drop a group whose members match the tag and the chain separately', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ chain: ['optimism'], tags: ['hot'] }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data).toHaveLength(0);
    });

    it('should drop a group none of whose members carries the tag', () => {
      const result = sortAndFilterAccounts(
        [group({ tags: ['hot', 'cold'] })],
        payload({ tags: ['hot', 'cold'] }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data).toHaveLength(0);
      expect(result.found).toBe(0);
      expect(result.total).toBe(1);
    });

    it('should not refine a group when only the address is filtered', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ addresses: ['0xAAA'] }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data[0].chains).toEqual(['eth', 'optimism']);
      expect(result.data[0].allChains).toBeUndefined();
    });

    it('should keep a group whose member matches both', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ chain: ['eth'], tags: ['hot'] }),
        { getAccounts: () => members(), getLabel: noLabel },
      );

      expect(result.data).toHaveLength(1);
    });

    /** Without a resolver there are no members to refine against, so the group stands as it is. */
    it('should leave the group alone when its members cannot be read', () => {
      const result = sortAndFilterAccounts(
        [group()],
        payload({ chain: ['eth'] }),
        { getLabel: noLabel },
      );

      expect(result.data[0].chains).toEqual(['eth', 'optimism']);
    });
  });
});
