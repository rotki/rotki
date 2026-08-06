import { describe, expect, it } from 'vitest';
import { accountAddActivity, accountRemoveActivity, type AccountSubject } from '@/modules/accounts/accounts.activity';

function subject(chain: string, address: string): AccountSubject {
  return { chain, target: { address, kind: 'address' } };
}

describe('account activity lanes', () => {
  // The lane is what serializes removals now that `awaitParallelExecution(..., 1)` is gone. A
  // removal that minted no lane would take the default one, which is uncapped, and the serial
  // behaviour would be lost silently rather than loudly.
  it('should put a removal on its chain lane', () => {
    expect(accountRemoveActivity.laneOf?.(subject('eth', '0xabc'))).toBe('accounts-remove:eth');
  });

  // Per chain, not one lane for every removal: the family cap of 1 is what makes a chain serial,
  // and a shared lane would serialize unrelated chains against each other instead.
  it('should give each chain its own removal lane', () => {
    const eth = accountRemoveActivity.laneOf?.(subject('eth', '0xabc'));
    expect(accountRemoveActivity.laneOf?.(subject('gnosis', '0xabc'))).not.toBe(eth);
  });

  // Additions and removals are independent operations; pooling them would make a removal wait on
  // an unrelated addition.
  it('should not share a lane between an addition and a removal on one chain', () => {
    const add = accountAddActivity.laneOf?.(subject('eth', '0xabc'));
    expect(accountRemoveActivity.laneOf?.(subject('eth', '0xabc'))).not.toBe(add);
  });
});
