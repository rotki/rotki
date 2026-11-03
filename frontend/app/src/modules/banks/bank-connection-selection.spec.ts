import type { BankManifest } from '@/modules/banks/types';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import {
  type BankSelectionOption,
  searchBankSelectionOptions,
  toBankSelectionOptions,
  toManifestSelection,
} from '@/modules/banks/bank-connection-selection';
import { fintsBanks } from '@/modules/banks/fints-bank-directory';

const MANUAL = 'Other bank (FinTS/HBCI)';

function manifest(connector: string, displayName: string): BankManifest {
  return createMock<BankManifest>({ connector, displayName });
}

function option(name: string, extra: Partial<BankSelectionOption> = {}): BankSelectionOption {
  return { connector: 'fints', id: `fints:${name}`, kind: 'fints', name, searchText: name.toLowerCase(), ...extra };
}

function names(options: readonly BankSelectionOption[]): string[] {
  return options.map(({ name }) => name);
}

describe('bank connection selection', () => {
  it('should list the dedicated connectors among the directory banks, then the manual FinTS option last', () => {
    const options = toBankSelectionOptions([manifest('qonto', 'Qonto'), manifest('fints', 'FinTS')], MANUAL);

    expect(options).toHaveLength(fintsBanks.length + 2);
    expect(options.at(-1)).toMatchObject({ connector: 'fints', id: 'fints:manual', kind: 'fints-manual', name: MANUAL });
    expect(options.filter(({ kind }) => kind === 'connector').map(({ connector }) => connector)).toEqual(['qonto']);
  });

  it('should turn the FinTS manifest into the manual option, and any other into its connector', () => {
    expect(toManifestSelection(manifest('fints', 'FinTS'), MANUAL).kind).toBe('fints-manual');
    expect(toManifestSelection(manifest('qonto', 'Qonto'), MANUAL)).toMatchObject({ id: 'connector:qonto', kind: 'connector', name: 'Qonto' });
  });

  it('should keep every option, in order, for an empty or blank query', () => {
    const options = [option('B'), option('A')];
    expect(names(searchBankSelectionOptions(options, '   '))).toEqual(['B', 'A']);
  });

  it('should rank an exact name above a prefix, a word and a substring match', () => {
    const options = [option('Xing Bank'), option('Banking Ing'), option('Ingolstadt Bank'), option('ING')];
    expect(names(searchBankSelectionOptions(options, 'ing'))).toEqual(['ING', 'Ingolstadt Bank', 'Banking Ing', 'Xing Bank']);
  });

  it('should ignore diacritics and case', () => {
    const options = [option('Sparkasse Münsterland Ost')];
    expect(names(searchBankSelectionOptions(options, 'MUNSTERLAND'))).toEqual(['Sparkasse Münsterland Ost']);
  });

  it('should need every term to match, each in any field', () => {
    const bank = { aliases: [], bankCodes: ['66090800'], city: 'Karlsruhe', endpoint: 'https://bbbank.example', id: '66090800', name: 'BBBank eG' };
    const options = [option('BBBank eG', { bank }), option('BBBank Berlin')];

    expect(names(searchBankSelectionOptions(options, 'bbbank karlsruhe'))).toEqual(['BBBank eG']);
    expect(names(searchBankSelectionOptions(options, 'bbbank nowhere'))).toEqual([]);
  });

  it('should find a bank by its exact BLZ ahead of one whose BLZ only contains the digits', () => {
    const exact = { aliases: [], bankCodes: ['12030000'], endpoint: 'https://a.example', id: 'a', name: 'Exact Bank' };
    const partial = { aliases: [], bankCodes: ['91203000'], endpoint: 'https://b.example', id: 'b', name: 'Another Bank' };
    const options = [option('Another Bank', { bank: partial }), option('Exact Bank', { bank: exact })];

    expect(names(searchBankSelectionOptions(options, '1203000'))).toEqual(['Another Bank', 'Exact Bank']);
    expect(names(searchBankSelectionOptions(options, '12030000'))).toEqual(['Exact Bank']);
  });

  it('should rank a name match above a match on the city alone', () => {
    const inCity = { aliases: [], bankCodes: ['10000000'], city: 'Hamburg', endpoint: 'https://c.example', id: 'c', name: 'Volksbank' };
    const options = [option('Volksbank', { bank: inCity }), option('Hamburger Sparkasse')];
    expect(names(searchBankSelectionOptions(options, 'hamburg'))).toEqual(['Hamburger Sparkasse', 'Volksbank']);
  });

  it('should find a bank by an alias', () => {
    const dkb = { aliases: ['DKB'], bankCodes: ['12030000'], endpoint: 'https://dkb.example', id: 'dkb', name: 'Deutsche Kreditbank Berlin' };
    expect(names(searchBankSelectionOptions([option('Deutsche Kreditbank Berlin', { bank: dkb })], 'dkb'))).toEqual(['Deutsche Kreditbank Berlin']);
  });
});
