import type {
  Accounts,
  AddressGroupWithBalance,
  Balances,
  BlockchainAccountWithBalance,
  XpubGroupWithBalance,
} from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { getAccountGroupId } from '@/modules/accounts/account-utils';
import { DeletionKind, planDeletion, removedAccounts, removedXpub, withoutRemoved } from './account-deletion';

const ADDRESS = '0x123';

function addressGroup(chains: string[], allChains?: string[]): AddressGroupWithBalance {
  return { address: ADDRESS, allChains, category: 'evm', chains, kind: 'address', type: 'group', value: bigNumberify(0) };
}

function xpubGroup(derivationPath?: string): XpubGroupWithBalance {
  return {
    amount: bigNumberify(0),
    category: 'bitcoin',
    chains: ['btc'],
    derivationPath,
    kind: 'xpub',
    nativeAsset: 'BTC',
    type: 'group',
    value: bigNumberify(0),
    xpub: 'xpub1',
  };
}

describe('planDeletion', () => {
  it('should delete validators by themselves', () => {
    const validators = [{ ...createTestBalance(32, 32), index: 1, publicKey: '0xvalidator', status: 'active' }];

    expect(planDeletion({ data: validators, type: 'validator' })).toStrictEqual({ kind: DeletionKind.VALIDATORS, validators });
  });

  it('should delete an account row on its own chain', () => {
    const account: BlockchainAccountWithBalance = {
      address: ADDRESS,
      amount: bigNumberify(0),
      chain: 'optimism',
      groupId: getAccountGroupId({ address: ADDRESS, chain: 'optimism', kind: 'address' }),
      kind: 'address',
      type: 'account',
      value: bigNumberify(0),
    };

    expect(planDeletion({ data: account, type: 'account' })).toStrictEqual({ address: ADDRESS, chain: 'optimism', kind: DeletionKind.ON_CHAIN });
  });

  it('should delete an xpub by its whole key', () => {
    expect(planDeletion({ data: xpubGroup('m/0'), type: 'account' })).toStrictEqual({
      chain: 'btc',
      key: { derivationPath: 'm/0', xpub: 'xpub1' },
      kind: DeletionKind.XPUB,
    });
  });

  it('should delete a group showing one chain on that chain', () => {
    expect(planDeletion({ data: addressGroup(['eth']), type: 'account' })).toStrictEqual({ address: ADDRESS, chain: 'eth', kind: DeletionKind.ON_CHAIN });
  });

  it('should delete a group showing a subset of its chains only on the chains it shows', () => {
    expect(planDeletion({ data: addressGroup(['eth', 'optimism'], ['eth', 'optimism', 'base']), type: 'account' })).toStrictEqual({
      address: ADDRESS,
      chains: ['eth', 'optimism'],
      kind: DeletionKind.ON_CHAINS,
    });
  });

  it('should delete a group showing all its chains everywhere under its own category', () => {
    const group: AddressGroupWithBalance = { ...addressGroup(['btc', 'bch']), category: 'bitcoin' };

    expect(planDeletion({ data: group, type: 'account' })).toStrictEqual({
      address: ADDRESS,
      category: 'bitcoin',
      chains: ['btc', 'bch'],
      kind: DeletionKind.EVERYWHERE,
    });
  });

  it('should leave out chains the backend does not know when counting what a group shows', () => {
    expect(planDeletion({ data: addressGroup(['eth', 'not-a-chain']), type: 'account' })).toStrictEqual({
      address: ADDRESS,
      chain: 'eth',
      kind: DeletionKind.ON_CHAIN,
    });
  });
});

describe('withoutRemoved', () => {
  const entry = { assets: { ETH: { address: createTestBalance(1, 10) } }, liabilities: {} };

  it('should drop the removed identities and their balances on the given chains only', () => {
    const accounts: Accounts = {
      base: [{ address: ADDRESS, chain: 'base', kind: 'address' }],
      eth: [{ address: ADDRESS, chain: 'eth', kind: 'address' }, { address: '0xother', chain: 'eth', kind: 'address' }],
    };
    const balances: Balances = { base: { [ADDRESS]: entry }, eth: { '0xother': entry, [ADDRESS]: entry } };

    expect(withoutRemoved({ accounts, balances }, removedAccounts([ADDRESS], ['eth']))).toStrictEqual({
      accounts: { base: accounts.base, eth: [{ address: '0xother', chain: 'eth', kind: 'address' }] },
      balances: { base: { [ADDRESS]: entry }, eth: { '0xother': entry } },
    });
  });

  it('should drop an xpub with the addresses derived from it, and keep the same xpub under another path', () => {
    const kept = [
      { chain: 'btc', derivationPath: 'm/1', kind: 'xpub', xpub: 'xpub1' },
      { address: 'bc1kept', chain: 'btc', kind: 'address', xpubParent: { derivationPath: 'm/1', xpub: 'xpub1' } },
    ] as const;
    const accounts: Accounts = {
      btc: [
        { chain: 'btc', derivationPath: 'm/0', kind: 'xpub', xpub: 'xpub1' },
        { address: 'bc1gone', chain: 'btc', kind: 'address', xpubParent: { derivationPath: 'm/0', xpub: 'xpub1' } },
        ...kept,
      ],
    };
    const balances: Balances = { btc: { bc1gone: entry, bc1kept: entry } };

    expect(withoutRemoved({ accounts, balances }, removedXpub({ derivationPath: 'm/0', xpub: 'xpub1' }, 'btc'))).toStrictEqual({
      accounts: { btc: [...kept] },
      balances: { btc: { bc1kept: entry } },
    });
  });

  it('should leave the state it was given untouched', () => {
    const accounts: Accounts = { eth: [{ address: ADDRESS, chain: 'eth', kind: 'address' }] };
    const balances: Balances = { eth: { [ADDRESS]: entry } };

    withoutRemoved({ accounts, balances }, removedAccounts([ADDRESS], ['eth']));

    expect(accounts.eth).toHaveLength(1);
    expect(balances.eth).toHaveProperty([ADDRESS]);
  });
});
