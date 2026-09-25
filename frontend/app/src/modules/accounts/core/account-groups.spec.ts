import type { Accounts, Balances } from '@/modules/accounts/blockchain-accounts';
import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { createAccount, createValidatorAccount, createXpubAccount } from '@/modules/accounts/create-account';
import { type AccountGroupPorts, accountGroups } from './account-groups';

const ports: AccountGroupPorts = {
  accountType: chain => (chain === 'btc' ? 'bitcoin' : 'evm'),
  isAssetIgnored: identifier => identifier === 'SPAM',
};

const xpubGroup = 'xpub1#btc';

const accounts: Accounts = {
  btc: [
    createXpubAccount({ addresses: null, derivationPath: null, label: 'savings', tags: ['cold', 'cold'], xpub: 'xpub1' }, { chain: 'btc', groupHeader: true, groupId: xpubGroup, nativeAsset: 'BTC' }),
    createAccount({ address: 'bc1-child-a', label: null, tags: null }, { chain: 'btc', groupId: xpubGroup, nativeAsset: 'BTC' }),
    createAccount({ address: 'bc1-child-b', label: null, tags: null }, { chain: 'btc', groupId: xpubGroup, nativeAsset: 'BTC' }),
    createAccount({ address: 'bc1-child-other', label: null, tags: null }, { chain: 'btc', groupId: xpubGroup, nativeAsset: 'OTHER' }),
  ],
  eth: [
    createAccount({ address: '0xmulti', label: 'main', tags: ['hot'] }, { chain: 'eth', nativeAsset: 'ETH' }),
    createAccount({ address: '0xsolo', label: null, tags: null }, { chain: 'eth', nativeAsset: 'ETH' }),
  ],
  eth2: [createValidatorAccount({ index: 1, publicKey: '0xvalidator', status: 'active' }, { chain: 'eth2', nativeAsset: 'ETH' })],
  optimism: [createAccount({ address: '0xmulti', label: null, tags: ['hot', 'l2'] }, { chain: 'optimism', nativeAsset: 'ETH' })],
};

const balances: Balances = {
  btc: {
    'bc1-child-a': { assets: { BTC: { address: createTestBalance(1, 100) } }, liabilities: {} },
    'bc1-child-b': { assets: { BTC: { address: createTestBalance(2, 200) } }, liabilities: {} },
    'bc1-child-other': { assets: { OTHER: { address: createTestBalance(5, 50) } }, liabilities: {} },
  },
  eth: {
    '0xmulti': {
      assets: { ETH: { address: createTestBalance(1, 10) }, SPAM: { address: createTestBalance(9, 999) } },
      liabilities: {},
    },
    '0xsolo': {
      assets: { DAI: { address: createTestBalance(5, 5) }, ETH: { address: createTestBalance(1, 10) } },
      liabilities: {},
    },
  },
  eth2: { '0xvalidator': { assets: { ETH: { address: createTestBalance(32, 320) } }, liabilities: {} } },
  optimism: { '0xmulti': { assets: { ETH: { address: createTestBalance(2, 20) } }, liabilities: {} } },
};

type Group = ReturnType<typeof accountGroups>[number];

function keyOf(group: Group): string {
  if ('address' in group.data)
    return group.data.address;
  return 'xpub' in group.data ? group.data.xpub : '';
}

function groupFor(key: string): Group | undefined {
  return accountGroups(accounts, balances, ports).find(group => keyOf(group) === key);
}

describe('accountGroups', () => {
  it('should give one row per address, then one per xpub, and none to validators or xpub children', () => {
    expect(accountGroups(accounts, balances, ports).map(keyOf)).toEqual(['0xmulti', '0xsolo', 'xpub1']);
  });

  it('should merge an address tracked on several chains, summing its value and leaving ignored assets out', () => {
    const multi = groupFor('0xmulti');
    expect(multi?.chains).toEqual(['eth', 'optimism']);
    expect(multi?.value.toFixed()).toBe('30');
    expect(multi?.tags).toEqual(['hot', 'l2']);
    expect(multi?.label).toBe('main');
    expect(multi?.expansion).toBe('accounts');
    expect(multi?.data).toEqual({ address: '0xmulti', type: 'address' });
    expect(multi?.category).toBe('evm');
  });

  it('should expand a lone account to its tokens only when it holds more than its native asset', () => {
    const solo = groupFor('0xsolo');
    expect(solo?.expansion).toBe('assets');
    expect(solo?.chains).toEqual(['eth']);

    const nativeOnly = accountGroups(
      { eth: [createAccount({ address: '0xsolo', label: null, tags: null }, { chain: 'eth', nativeAsset: 'ETH' })] },
      { eth: { '0xsolo': { assets: { ETH: { address: createTestBalance(1, 10) } }, liabilities: {} } } },
      ports,
    );
    expect(nativeOnly[0].expansion).toBeUndefined();
  });

  it('should sum an xpub\'s value over every derived address but its amount over its native asset only', () => {
    const xpub = groupFor('xpub1');
    expect(xpub?.amount?.toFixed()).toBe('3');
    expect(xpub?.value.toFixed()).toBe('350');
    expect(xpub?.expansion).toBe('accounts');
    expect(xpub?.tags).toEqual(['cold']);
    expect(xpub?.category).toBe('bitcoin');
  });
});
