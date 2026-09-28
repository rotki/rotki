import type { BlockchainAccountWithBalance } from '@/modules/accounts/blockchain-accounts';
import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { type AccountGroupId, getAccountAddress, getAccountGroupId, getXpubGroupId } from '@/modules/accounts/account-utils';
import { accountAssetBalances, accountsByGroup, topTokens, xpubNativeHolding } from './account-assets';

function account(address: string, groupId?: AccountGroupId): BlockchainAccountWithBalance {
  return {
    address,
    amount: bigNumberify(1),
    chain: 'eth',
    groupId: groupId ?? getAccountGroupId({ address, chain: 'eth', kind: 'address' }),
    kind: 'address',
    type: 'account',
    value: bigNumberify(1),
  };
}

describe('accountAssetBalances', () => {
  const ports = {
    isAssetIgnored: (identifier: string): boolean => identifier === 'SPAM',
    resolveIdentifier: (identifier: string): string => (identifier === 'ETH2' ? 'ETH' : identifier),
  };

  it('should sum each asset across protocols, merging identifiers that resolve to the same asset', () => {
    const rows = accountAssetBalances({
      ETH: { 'address': createTestBalance(1, 10), 'uniswap-v3': createTestBalance(2, 20) },
      ETH2: { 'eth2-staking': createTestBalance(3, 30) },
    }, ports);
    expect(rows.map(({ amount, asset }) => `${asset}:${amount.toFixed()}`)).toEqual(['ETH:6']);
  });

  it('should leave out ignored assets and empty protocol entries', () => {
    const rows = accountAssetBalances({
      DAI: { address: createTestBalance(0, 0) },
      SPAM: { address: createTestBalance(9, 9) },
    }, ports);
    expect(rows).toEqual([]);
  });
});

describe('accountsByGroup', () => {
  it('should key accounts by group id, a standalone account keyed by its own', () => {
    const g1 = getXpubGroupId({ xpub: 'xpub1' }, 'btc');
    const standalone = account('0x3');
    const groups = accountsByGroup([account('0x1', g1), account('0x2', g1), standalone]);
    expect([...groups.keys()]).toEqual([g1, standalone.groupId]);
    expect(groups.get(g1)?.map(getAccountAddress)).toEqual(['0x1', '0x2']);
  });
});

describe('topTokens', () => {
  it('should keep asset, amount and value only, highest value first', () => {
    const dai: AssetBalanceWithPrice = { amount: bigNumberify(1), asset: 'DAI', price: bigNumberify(1), value: bigNumberify(1) };
    const tokens = topTokens([dai, { amount: bigNumberify(1), asset: 'ETH', value: bigNumberify(10) }]);
    expect(tokens.map(token => token.asset)).toEqual(['ETH', 'DAI']);
    expect(Object.keys(tokens[1]).sort()).toEqual(['amount', 'asset', 'value']);
  });
});

describe('xpubNativeHolding', () => {
  it('should show an xpub as one row of its native asset', () => {
    const holding = xpubNativeHolding({
      amount: bigNumberify(2),
      category: 'bitcoin',
      chains: ['btc'],
      kind: 'xpub',
      nativeAsset: 'BTC',
      type: 'group',
      value: bigNumberify(200),
      xpub: 'xpub1',
    });
    expect(holding?.asset).toBe('BTC');
    expect(holding?.amount.toFixed()).toBe('2');
  });

  it('should give nothing for an address account', () => {
    expect(xpubNativeHolding(account('0x1'))).toBeUndefined();
  });
});
