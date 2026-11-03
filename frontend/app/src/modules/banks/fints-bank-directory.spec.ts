import { describe, expect, it } from 'vitest';
import {
  type FintsBank,
  FintsBankDirectory,
  fintsBankDirectory,
  fintsBankLogo,
  fintsBanks,
  toFintsBankOptions,
} from '@/modules/banks/fints-bank-directory';

function bankNamed(name: string): FintsBank | undefined {
  return fintsBanks.find(bank => bank.name.includes(name));
}

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
      g: {},
      h: 'a'.repeat(64),
      v: '2026-01-01',
    };
    expect(FintsBankDirectory.safeParse({ ...directory, b: [['One', '', 0, '12345679']] }).success).toBe(true);
    expect(FintsBankDirectory.safeParse(directory).success).toBe(false);
    expect(FintsBankDirectory.safeParse({ ...directory, b: [['One', '', 1, '12345679']] }).success).toBe(false);
    expect(FintsBankDirectory.safeParse({ ...directory, b: [['One', '', 0, '12345679']], e: ['http://one.example/fints'] }).success).toBe(false);
  });

  it('should reject a logo naming a missing institution, one that already has a logo, or an unpackaged file', () => {
    const directory = {
      b: [['One', '', 0, '12345678']],
      e: ['https://one.example/fints'],
      g: { 'bank_one.svg': [0] },
      h: 'a'.repeat(64),
      v: '2026-01-01',
    };
    expect(FintsBankDirectory.safeParse(directory).success).toBe(true);
    expect(FintsBankDirectory.safeParse({ ...directory, g: { 'bank_one.svg': [1] } }).success).toBe(false);
    expect(FintsBankDirectory.safeParse({ ...directory, g: { 'bank_one.svg': [0], 'bank_two.svg': [0] } }).success).toBe(false);
    expect(FintsBankDirectory.safeParse({ ...directory, g: { '../one.svg': [0] } }).success).toBe(false);
  });

  it('should give a bank the logo of its brand or banking group, and none to a bank without one', () => {
    expect(bankNamed('Deutsche Kreditbank')?.logo).toBe('bank_dkb.svg');
    expect(bankNamed('Berliner Sparkasse')?.logo).toBe('bank_sparkasse.svg');
    expect(bankNamed('Allgemeine Beamten Bank')?.logo).toBeUndefined();
  });

  it('should find a logo by any of the bank\'s codes', () => {
    expect(fintsBankLogo('20041199')).toBe('bank_comdirect.svg');
    expect(fintsBankLogo('12030000')).toBe('bank_dkb.svg');
    expect(fintsBankLogo('10030400')).toBeUndefined();
    expect(fintsBankLogo('00000000')).toBeUndefined();
  });

  it('should group comdirect into one searchable institution with all its BLZs', () => {
    const matches = fintsBanks.filter(bank => bank.name.toLowerCase().includes('comdirect'));
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
