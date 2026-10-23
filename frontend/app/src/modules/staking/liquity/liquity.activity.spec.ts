import { describe, expect, it } from 'vitest';
import { liquityActivity } from '@/modules/staking/liquity/liquity.activity';
import { ActivityPart } from '@/modules/task-center/core/types';

describe('liquity activity ids', () => {
  it('should key each liquity query by its part', () => {
    expect(liquityActivity.id({ part: ActivityPart.BALANCES })).toBe('liquity:balances');
    expect(liquityActivity.id({ part: ActivityPart.POOLS })).toBe('liquity:pools');
    expect(liquityActivity.id({ part: ActivityPart.STAKE })).toBe('liquity:stake');
    expect(liquityActivity.id({ part: ActivityPart.STATISTICS })).toBe('liquity:statistics');
  });
});
