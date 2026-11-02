import { describe, expect, it } from 'vitest';
import { SOLANA_CHAIN } from '@/modules/assets/types';
import { ChainFamily, chainFamilyAt } from '@/modules/history/management/forms/common/chain-location';

/** The chains an evm swap or event can be on, as the supported chains name them. */
const evmLocations = ['ethereum', 'optimism'];

describe('chainFamilyAt', () => {
  it.each([
    { chain: ChainFamily.EVM, location: 'optimism' },
    { chain: ChainFamily.SOLANA, location: SOLANA_CHAIN },
    { chain: ChainFamily.BITCOIN, location: 'bitcoin' },
    { chain: ChainFamily.BITCOIN, location: 'bitcoin_cash' },
    { chain: undefined, location: 'kraken' },
    { chain: undefined, location: '' },
  ])('should put "$location" on the $chain chain', ({ chain, location }) => {
    expect(chainFamilyAt(location, evmLocations)).toBe(chain);
  });

  it('should not count an evm chain whose locations have not loaded yet', () => {
    expect(chainFamilyAt('ethereum', [])).toBeUndefined();
  });
});
