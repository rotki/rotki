import { describe, expect, it } from 'vitest';
import {
  accountAddActivity,
  accountRemoveActivity,
  type AccountSubject,
  ensResolveActivity,
  evmAccountDetectionActivity,
} from '@/modules/accounts/accounts.activity';
import { setDigest } from '@/modules/core/common/data/digest';
import { activityParts } from '@/modules/task-center/core/types';

function subject(chain: string, address: string): AccountSubject {
  return { chain, target: { address, kind: 'address' } };
}

describe('account activity lanes', () => {
  it('should put a removal on its chain lane, since the default lane is uncapped and would lose the serial behaviour silently', () => {
    expect(accountRemoveActivity.laneOf?.(subject('eth', '0xabc'))).toBe('accounts-remove:eth');
  });

  it('should give each chain its own removal lane, so unrelated chains are not serialized against each other', () => {
    const eth = accountRemoveActivity.laneOf?.(subject('eth', '0xabc'));
    expect(accountRemoveActivity.laneOf?.(subject('gnosis', '0xabc'))).not.toBe(eth);
  });

  it('should not share a lane between an addition and a removal on one chain, so a removal never waits on an unrelated addition', () => {
    const add = accountAddActivity.laneOf?.(subject('eth', '0xabc'));
    expect(accountRemoveActivity.laneOf?.(subject('eth', '0xabc'))).not.toBe(add);
  });
});

describe('account activity ids', () => {
  it('should drop the CashAddr prefix, in either case, so the address survives as one part', () => {
    const cashAddress = 'qpmmlusvvrjj9ha2xdgv8xcrpfwsqn5rngt3k26ve2';
    const id = accountAddActivity.id(subject('bch', `bitcoincash:${cashAddress}`));

    expect(id).toBe(`accounts:add:bch:${cashAddress}`);
    expect(accountAddActivity.id(subject('bch', `BITCOINCASH:${cashAddress.toUpperCase()}`))).toBe(`accounts:add:bch:${cashAddress.toUpperCase()}`);
    expect(activityParts(id)).toStrictEqual(['add', 'bch', cashAddress]);
  });

  it('should give a prefixed and an unprefixed paste of one address the same addition and removal ids', () => {
    const cashAddress = 'qpmmlusvvrjj9ha2xdgv8xcrpfwsqn5rngt3k26ve2';
    expect(accountAddActivity.id(subject('bch', `bitcoincash:${cashAddress}`))).toBe(accountAddActivity.id(subject('bch', cashAddress)));
    expect(accountRemoveActivity.id(subject('bch', `bitcoincash:${cashAddress}`))).toBe(accountRemoveActivity.id(subject('bch', cashAddress)));
  });

  it('should give the EVM detection its fixed id', () => {
    expect(evmAccountDetectionActivity.id()).toBe('accounts:detect');
  });

  it('should key an ENS resolve by the address set, in any order', () => {
    expect(ensResolveActivity.id({ addresses: ['0xa', '0xb'] })).toBe(`accounts:ens:${setDigest(['0xa', '0xb'])}`);
    expect(ensResolveActivity.id({ addresses: ['0xb', '0xa'] })).toBe(ensResolveActivity.id({ addresses: ['0xa', '0xb'] }));
  });

  it('should give a forced resolve of other addresses its own id, so it never joins one in flight', () => {
    expect(ensResolveActivity.id({ addresses: ['0xa'] })).not.toBe(ensResolveActivity.id({ addresses: ['0xb'] }));
  });

  it('should keep both outside the add and remove prefixes the account tables read', () => {
    for (const id of [ensResolveActivity.id({ addresses: ['0xa'] }), evmAccountDetectionActivity.id()]) {
      expect(id.startsWith(`accounts:${accountAddActivity.partsWithin([]).join(':')}`)).toBe(false);
      expect(id.startsWith(`accounts:${accountRemoveActivity.partsWithin([]).join(':')}`)).toBe(false);
    }
  });
});
