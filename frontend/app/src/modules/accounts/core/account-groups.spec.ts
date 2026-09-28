import type { Accounts, Balances } from '@/modules/accounts/blockchain-accounts';
import { createTestBalance } from '@test/utils/create-data';
import { assert, describe, expect, it } from 'vitest';
import { getAccountAddress, isXpubAccount } from '@/modules/accounts/account-utils';
import { createAccount, createValidatorAccount, createXpubAccount } from '@/modules/accounts/create-account';
import { type AccountGroupPorts, accountGroups } from './account-groups';

const ports: AccountGroupPorts = {
  accountType: chain => (chain === 'btc' ? 'bitcoin' : 'evm'),
  isAssetIgnored: identifier => identifier === 'SPAM',
  nativeAssetOf: chain => (chain === 'btc' ? 'BTC' : 'ETH'),
};

const xpub1 = { xpub: 'xpub1' };

const accounts: Accounts = {
  btc: [
    createXpubAccount({ addresses: null, derivationPath: null, label: 'savings', tags: ['cold', 'cold'], xpub: 'xpub1' }, 'btc'),
    createAccount({ address: 'bc1-child-a', label: null, tags: null }, 'btc', xpub1),
    createAccount({ address: 'bc1-child-b', label: null, tags: null }, 'btc', xpub1),
    createAccount({ address: 'bc1-child-other', label: null, tags: null }, 'btc', xpub1),
  ],
  eth: [
    createAccount({ address: '0xmulti', label: 'main', tags: ['hot'] }, 'eth'),
    createAccount({ address: '0xsolo', label: null, tags: null }, 'eth'),
  ],
  eth2: [createValidatorAccount({ index: 1, publicKey: '0xvalidator', status: 'active' }, 'eth2')],
  optimism: [createAccount({ address: '0xmulti', label: null, tags: ['hot', 'l2'] }, 'optimism')],
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
  return getAccountAddress(group);
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
    expect(multi?.kind).toBe('address');
    expect(multi?.category).toBe('evm');
  });

  it('should expand a lone account to its tokens only when it holds more than its native asset', () => {
    const solo = groupFor('0xsolo');
    expect(solo?.expansion).toBe('assets');
    expect(solo?.chains).toEqual(['eth']);

    const nativeOnly = accountGroups(
      { eth: [createAccount({ address: '0xsolo', label: null, tags: null }, 'eth')] },
      { eth: { '0xsolo': { assets: { ETH: { address: createTestBalance(1, 10) } }, liabilities: {} } } },
      ports,
    );
    expect(nativeOnly[0].expansion).toBeUndefined();
  });

  it('should show a tracked address whose balances have not loaded yet as an empty, unexpandable row', () => {
    const fresh = accountGroups(
      { eth: [createAccount({ address: '0xnew', label: null, tags: null }, 'eth')] },
      {},
      ports,
    );
    expect(fresh).toHaveLength(1);
    expect(fresh[0].value.toFixed()).toBe('0');
    expect(fresh[0].expansion).toBeUndefined();
  });

  it('should show an xpub with no derived addresses as an empty, unexpandable row', () => {
    const lone = accountGroups(
      { btc: [createXpubAccount({ addresses: null, derivationPath: null, label: null, tags: null, xpub: 'xpub2' }, 'btc')] },
      {},
      ports,
    );
    expect(lone).toHaveLength(1);
    expect(lone[0].value.toFixed()).toBe('0');
    expect(lone[0].expansion).toBeUndefined();
    expect(lone[0].tags).toBeUndefined();
  });

  it('should sum an xpub\'s value over every derived address but its amount over its native asset only', () => {
    const xpub = groupFor('xpub1');
    assert(xpub && isXpubAccount(xpub));
    expect(xpub.amount.toFixed()).toBe('3');
    expect(xpub.value.toFixed()).toBe('350');
    expect(xpub.nativeAsset).toBe('BTC');
    expect(xpub.expansion).toBe('accounts');
    expect(xpub.tags).toEqual(['cold']);
    expect(xpub.category).toBe('bitcoin');
  });

  it('should count only the addresses derived from that xpub, not those of another one on the same chain', () => {
    const withSibling: Accounts = {
      btc: [
        ...accounts.btc,
        createXpubAccount({ addresses: null, derivationPath: 'm/1', label: null, tags: null, xpub: 'xpub1' }, 'btc'),
        createAccount({ address: 'bc1-sibling', label: null, tags: null }, 'btc', { derivationPath: 'm/1', xpub: 'xpub1' }),
      ],
    };
    const siblingBalances: Balances = {
      btc: { ...balances.btc, 'bc1-sibling': { assets: { BTC: { address: createTestBalance(7, 700) } }, liabilities: {} } },
    };

    const [first, second] = accountGroups(withSibling, siblingBalances, ports).filter(isXpubAccount);
    expect(first.value.toFixed()).toBe('350');
    expect(second.derivationPath).toBe('m/1');
    expect(second.value.toFixed()).toBe('700');
  });

  it('should leave out the groups of a chain without a category, which no accounts page lists', () => {
    const onlyEvm: AccountGroupPorts = { ...ports, accountType: chain => (chain === 'btc' ? undefined : 'evm') };
    expect(accountGroups(accounts, balances, onlyEvm).map(keyOf)).toEqual(['0xmulti', '0xsolo']);

    const onlyBitcoin: AccountGroupPorts = { ...ports, accountType: chain => (chain === 'btc' ? 'bitcoin' : undefined) };
    expect(accountGroups(accounts, balances, onlyBitcoin).map(keyOf)).toEqual(['xpub1']);
  });
});
