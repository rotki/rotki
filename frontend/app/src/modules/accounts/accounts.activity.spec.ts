import { describe, expect, it } from 'vitest';
import { accountAddActivity, accountRemoveActivity, type AccountSubject } from '@/modules/accounts/accounts.activity';

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
