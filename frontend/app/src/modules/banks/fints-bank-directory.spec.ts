import { describe, expect, it } from 'vitest';
import {
  FintsBankDirectory,
  fintsBankDirectory,
  fintsBanks,
  searchFintsBanks,
  toFintsBankOptions,
} from '@/modules/banks/fints-bank-directory';

describe('fintsBankDirectory', () => {
  it('should ship the complete compact registry catalog with reproducible provenance', () => {
    expect(FintsBankDirectory.safeParse(fintsBankDirectory).success).toBe(true);
    expect(fintsBankDirectory.v).toBe('2026-10-12');
    expect(fintsBankDirectory.h).toBe('6962204a7695802bca600abe971cdf8aaadef7e4ce3b3fac342f526adaabf924');
    expect(fintsBanks).toHaveLength(1694);
    expect(fintsBanks.reduce((total, bank) => total + bank.bankCodes.length, 0)).toBe(1716);
  });

  it('should reject duplicate bank codes, unsafe endpoints, and missing endpoint indexes', () => {
    const directory = {
      b: [
        ['One', '', 0, '12345678'],
        ['Two', '', 0, '12345678'],
      ],
      e: ['https://one.example/fints'],
      h: 'a'.repeat(64),
      v: '2026-01-01',
    };
    expect(FintsBankDirectory.safeParse(directory).success).toBe(false);
    expect(FintsBankDirectory.safeParse({ ...directory, b: [['One', '', 1, '12345679']] }).success).toBe(false);
    expect(FintsBankDirectory.safeParse({ ...directory, b: [['One', '', 0, '12345679']], e: ['http://one.example/fints'] }).success).toBe(false);
  });

  it('should find institutions by name, alias, city, and every eight-digit BLZ', () => {
    expect(searchFintsBanks('BBBank Karlsruhe')[0]?.bankCodes).toContain('66090800');
    expect(searchFintsBanks('66090800')[0]?.name).toBe('BBBank eG');
    expect(searchFintsBanks('SKG BANK')[0]?.bankCodes).toContain('12030000');
  });

  it('should group comdirect into one searchable institution with all its BLZs', () => {
    const matches = searchFintsBanks('comdirect');
    expect(matches).toHaveLength(1);
    expect(matches[0]?.bankCodes).toEqual([
      '20041111',
      '20041133',
      '20041144',
      '20041155',
      '20041166',
      '20041177',
      '20041188',
      '20041199',
    ]);
    expect(toFintsBankOptions(matches)[0]?.searchText).toContain('20041199');
  });
});
