import { describe, expect, it } from 'vitest';
import {
  FintsBankDirectory,
  fintsBankDirectory,
  searchFintsBanks,
  toFintsBankOptions,
} from '@/modules/banks/fints-bank-directory';

describe('fintsBankDirectory', () => {
  it('should ship a valid, versioned catalog with explicit provenance', () => {
    expect(FintsBankDirectory.safeParse(fintsBankDirectory).success).toBe(true);
    expect(fintsBankDirectory.version).not.toBe('');
    expect(fintsBankDirectory.provenance).toContain('bank-published');
  });

  it('should reject duplicate bank codes and unsafe endpoints', () => {
    const duplicate = {
      banks: [
        { aliases: [], blz: '12345678', endpoint: 'https://one.example/fints', name: 'One', source: 'https://one.example' },
        { aliases: [], blz: '12345678', endpoint: 'https://two.example/fints', name: 'Two', source: 'https://two.example' },
      ],
      provenance: 'test',
      version: '1',
    };
    expect(FintsBankDirectory.safeParse(duplicate).success).toBe(false);
    expect(FintsBankDirectory.safeParse({
      ...duplicate,
      banks: [{ ...duplicate.banks[0], blz: '12345679', endpoint: 'http://one.example/fints' }],
    }).success).toBe(false);
  });

  it('should find banks by name, alias, and eight-digit BLZ', () => {
    expect(searchFintsBanks('GLS')).toHaveLength(1);
    expect(searchFintsBanks('gemeinschaftsbank Bochum')[0]?.blz).toBe('43060967');
    expect(searchFintsBanks('66090800')[0]?.name).toBe('BBBank eG');
  });

  it('should retain ambiguous names as distinct, labelled options', () => {
    const matches = searchFintsBanks('comdirect');
    expect(matches).toHaveLength(4);
    expect(new Set(matches.map(bank => bank.blz)).size).toBe(4);
    expect(toFintsBankOptions(matches).every(option => option.searchText.includes(option.blz))).toBe(true);
  });
});
