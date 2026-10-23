import { assert, describe, expect, it } from 'vitest';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import {
  krakenStakingActivity,
  stakingPerformanceActivity,
  stakingRowsActivity,
  validatorAddActivity,
  validatorAddLabel,
  validatorsActivity,
} from '@/modules/staking/staking.activity';
import { activityIdHasPrefix, ActivityPart } from '@/modules/task-center/core/types';

const publicKey = '0xb0456681b8a0c7c4d4b1b9a48fa6c1bb4bc2a1c5b62f5a0b39c7fa4e53e0c1c1f3d5c6a8b3d2e1f0a9b8c7d6e5f4a3b2';

/** Literal ids on purpose, as in `decode.activity.spec.ts`. */
describe('staking activity ids', () => {
  it('should key a validator addition by its public key, else its index', () => {
    expect(validatorAddActivity.id({ publicKey })).toBe(`staking:add:${publicKey}`);
    expect(validatorAddActivity.id({ validatorIndex: '12345' })).toBe('staking:add:12345');
    expect(validatorAddActivity.id({ publicKey, validatorIndex: '12345' })).toBe(`staking:add:${publicKey}`);
  });

  it('should treat the empty public key the form submits for an index-only addition as absent', () => {
    expect(validatorAddActivity.id({ publicKey: '', validatorIndex: '12345' })).toBe('staking:add:12345');
  });

  it('should give two index-only additions distinct ids, so the second is never handed the first one\'s promise', () => {
    expect(validatorAddActivity.id({ publicKey: '', validatorIndex: '5' }))
      .not
      .toBe(validatorAddActivity.id({ publicKey: '', validatorIndex: '9' }));
  });

  it('should key an addition with no validator by an empty part', () => {
    expect(validatorAddActivity.id({})).toBe('staking:add:');
  });

  it('should put every addition under the add prefix the validator list and performance go stale on', () => {
    const within = validatorAddActivity.partsWithin([]);
    expect(within).toStrictEqual(['add']);
    expect(activityIdHasPrefix(validatorAddActivity.id({ validatorIndex: '1' }), validatorAddActivity.kind, ...within)).toBe(true);
  });

  it('should give the fixed staking queries their ids', () => {
    expect(validatorsActivity.id()).toBe('staking:validators');
    expect(stakingPerformanceActivity.id()).toBe('staking:performance');
    expect(krakenStakingActivity.id()).toBe('staking:kraken');
  });

  it('should key staking rows by location', () => {
    expect(stakingRowsActivity.id({ part: ActivityPart.HYPERLIQUID })).toBe('staking:hyperliquid');
    expect(stakingRowsActivity.id({ part: ActivityPart.SOLANA })).toBe('staking:solana');
  });
});

describe('validatorAddLabel', () => {
  it('should name the validator, truncated', () => {
    const label = validatorAddLabel({ publicKey });
    assert(typeof label !== 'string');
    expect(label.key).toBe('task_center.activity.staking.add_validator');
    expect(label.params).toStrictEqual({ validator: truncateAddress(publicKey) });
  });

  it('should name an index-only addition by its index, as it is, since it is too short to truncate', () => {
    const label = validatorAddLabel({ publicKey: '', validatorIndex: '12345' });
    assert(typeof label !== 'string');
    expect(label.params).toStrictEqual({ validator: '12345' });
  });

  it('should name no validator when the form gave none', () => {
    const label = validatorAddLabel({});
    assert(typeof label !== 'string');
    expect(label.params).toStrictEqual({ validator: '' });
  });
});
