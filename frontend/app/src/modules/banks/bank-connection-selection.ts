import type { BankManifest } from '@/modules/banks/types';
import { type FintsBank, toFintsBankOptions } from '@/modules/banks/fints-bank-directory';

export interface BankSelectionOption {
  bank?: FintsBank;
  id: string;
  kind: 'connector' | 'fints' | 'fints-manual';
  connector: string;
  name: string;
  searchText: string;
}

function normalizeSearch(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase();
}

function primaryMatchRank(value: string, term: string): number | undefined {
  if (value === term)
    return 0;
  if (value.startsWith(term))
    return 1;
  if (value.split(/[^\p{Letter}\p{Number}]+/u).some(word => word.startsWith(term)))
    return 2;
  if (value.includes(term))
    return 3;
  return undefined;
}

interface SearchFields {
  bankCodes: string[];
  city?: string;
  fallback: string;
  names: string[];
}

function termMatchRank({ bankCodes, city, fallback, names }: SearchFields, term: string): number | undefined {
  const nameRanks = names
    .map(name => primaryMatchRank(name, term))
    .filter((rank): rank is number => rank !== undefined);
  if (nameRanks.length > 0)
    return Math.min(...nameRanks);
  if (bankCodes.includes(term))
    return 0;
  if (bankCodes.some(bankCode => bankCode.includes(term)))
    return 4;
  if (city?.includes(term))
    return 10 + (city.startsWith(term) ? 0 : 1);
  if (fallback.includes(term))
    return 20;
  return undefined;
}

function optionMatchRank(option: BankSelectionOption, query: string): number | undefined {
  const terms = normalizeSearch(query).trim().split(/\s+/u).filter(Boolean);
  const fields: SearchFields = {
    bankCodes: option.bank?.bankCodes ?? [],
    city: option.bank?.city ? normalizeSearch(option.bank.city) : undefined,
    fallback: normalizeSearch(option.searchText),
    names: [option.name, ...(option.bank?.aliases ?? [])].map(normalizeSearch),
  };
  let total = 0;
  for (const term of terms) {
    const termRank = termMatchRank(fields, term);
    if (termRank === undefined)
      return undefined;
    total += termRank;
  }
  return total;
}

export function searchBankSelectionOptions(
  options: readonly BankSelectionOption[],
  query: string,
): BankSelectionOption[] {
  if (normalizeSearch(query).trim() === '')
    return [...options];
  return options
    .map((option): { option: BankSelectionOption; rank: number } | undefined => {
      const rank = optionMatchRank(option, query);
      return rank === undefined ? undefined : { option, rank };
    })
    .filter((entry): entry is { option: BankSelectionOption; rank: number } => entry !== undefined)
    .sort((left, right) => left.rank - right.rank
      || left.option.name.localeCompare(right.option.name, 'de')
      || (left.option.bank?.city ?? '').localeCompare(right.option.bank?.city ?? '', 'de'))
    .map(({ option }) => option);
}

function toManualFintsSelection(manualName: string): BankSelectionOption {
  return {
    id: 'fints:manual',
    kind: 'fints-manual',
    connector: 'fints',
    name: manualName,
    searchText: `${manualName} fints hbci manual`.toLocaleLowerCase(),
  };
}

export function toManifestSelection(manifest: BankManifest, manualName: string): BankSelectionOption {
  if (manifest.connector === 'fints')
    return toManualFintsSelection(manualName);
  return {
    id: `connector:${manifest.connector}`,
    kind: 'connector',
    connector: manifest.connector,
    name: manifest.displayName,
    searchText: `${manifest.displayName} ${manifest.connector}`.toLocaleLowerCase(),
  };
}

export function toBankSelectionOptions(manifests: readonly BankManifest[], manualName: string): BankSelectionOption[] {
  const connectors: BankSelectionOption[] = manifests
    .filter(({ connector }) => connector !== 'fints')
    .map(manifest => toManifestSelection(manifest, manualName));
  const banks: BankSelectionOption[] = toFintsBankOptions().map(bank => ({
    bank,
    id: `fints:${bank.id}`,
    kind: 'fints',
    connector: 'fints',
    name: bank.name,
    searchText: bank.searchText,
  }));

  return [...connectors, ...banks]
    .sort((left, right) => left.name.localeCompare(right.name, 'de'))
    .concat(toManualFintsSelection(manualName));
}
