import { describe, expect, it } from 'vitest';
import { airdropsActivity } from '@/modules/airdrops/airdrops.activity';

describe('airdrops activity ids', () => {
  it('should give the airdrop query the bare kind', () => {
    expect(airdropsActivity.id()).toBe('airdrops');
  });
});
