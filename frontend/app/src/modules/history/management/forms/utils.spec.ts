import { describe, expect, it } from 'vitest';
import { getAssetMovementsType } from '@/modules/history/management/forms/utils';

describe('getAssetMovementsType', () => {
  it('should read a receive as a deposit', () => {
    expect(getAssetMovementsType('receive')).toBe('deposit');
  });

  it.each(['spend', 'fee', ''])('should read %j as a withdrawal', (subtype) => {
    expect(getAssetMovementsType(subtype)).toBe('withdrawal');
  });
});
