import { describe, expect, it } from 'vitest';
import { setDigest } from '@/modules/core/common/data/digest';
import {
  conflictResolutionActivity,
  repullEthStakingActivity,
  repullExchangeEventsActivity,
  repullTransactionsActivity,
} from '@/modules/history/events/tx/repulling.activity';
import { UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';

const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

/** Literal ids on purpose, as in `decode.activity.spec.ts`. */
describe('repulling activity ids', () => {
  it('should key a transaction re-pull by every field of the request', () => {
    expect(repullTransactionsActivity.id({ address, chain: 'eth', fromTimestamp: 10, toTimestamp: 20 }))
      .toBe(`repulling:transactions:${address}:eth:10:20`);
  });

  it('should keep an absent bound in the identity, so "before X" and "X to Y" never dedup', () => {
    expect(repullTransactionsActivity.id({ toTimestamp: 20 })).toBe('repulling:transactions:::0:20');
    expect(repullTransactionsActivity.id({ toTimestamp: 20 }))
      .not
      .toBe(repullTransactionsActivity.id({ fromTimestamp: 10, toTimestamp: 20 }));
  });

  it('should key an exchange re-pull by location, name and range', () => {
    expect(repullExchangeEventsActivity.id({ location: 'kraken', name: 'Main', toTimestamp: 20 })).toBe('repulling:exchange:kraken:Main:0:20');
  });

  it('should key an ETH staking re-pull by entry type, range and the digests of its filters', () => {
    expect(repullEthStakingActivity.id({ addresses: [address], entryType: 'eth_withdrawal_event', fromTimestamp: 10, validatorIndices: [7, 3] }))
      .toBe(`repulling:stake:eth_withdrawal_event:10:0:${setDigest(['3', '7'])}:${setDigest([address])}`);
  });

  it('should give re-pulls of one kind and range for different validators distinct ids', () => {
    const base = { entryType: 'eth_withdrawal_event', fromTimestamp: 10, toTimestamp: 20 };
    expect(repullEthStakingActivity.id({ ...base, validatorIndices: [1] }))
      .not
      .toBe(repullEthStakingActivity.id({ ...base, validatorIndices: [2] }));
  });

  it('should give the conflict resolution its fixed id, on the umbrella lane', () => {
    expect(conflictResolutionActivity.id()).toBe('repulling:run:internal-tx-conflicts');
    expect(conflictResolutionActivity.laneOf?.()).toBe(UMBRELLA_LANE);
  });
});
