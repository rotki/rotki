import { createTestBalance } from '@test/utils/create-data';
import { describe, expect, it } from 'vitest';
import { heldAssets } from './held-assets';

describe('heldAssets', () => {
  it('should list each asset once across sources', () => {
    const held = heldAssets([
      { BTC: { kraken: createTestBalance(1, 1) } },
      { BTC: { address: createTestBalance(1, 1) }, DAI: { makerdao: createTestBalance(1, 1) } },
    ]);
    expect(held.sort()).toEqual(['BTC', 'DAI']);
  });

  it('should add the assets priced the same as a held one', () => {
    expect(heldAssets([{ ETH: { address: createTestBalance(1, 1) } }]).sort()).toEqual(['ETH', 'ETH2']);
  });
});
