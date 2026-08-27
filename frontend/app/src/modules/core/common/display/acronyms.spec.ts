import { describe, expect, it } from 'vitest';
import { capitalizeAcronyms } from '@/modules/core/common/display/acronyms';

describe('capitalizeAcronyms', () => {
  it('should restore acronym casing a case normalizer lowercased', () => {
    expect(capitalizeAcronyms('Evm swap event')).toBe('EVM swap event');
    expect(capitalizeAcronyms('Eth withdrawal event')).toBe('ETH withdrawal event');
  });

  it('should leave a value with no acronym alone', () => {
    expect(capitalizeAcronyms('Asset movement event')).toBe('Asset movement event');
  });

  it('should not touch a word that merely starts with an acronym', () => {
    expect(capitalizeAcronyms('Ethereum staking')).toBe('Ethereum staking');
  });
});
