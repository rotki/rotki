import type { BankManifest } from '@/modules/banks/types';
import { type FintsBank, toFintsBankOptions } from '@/modules/banks/fints-bank-directory';

export interface BankSelectionOption {
  bank?: FintsBank;
  id: string;
  kind: 'connector' | 'fints' | 'fints-manual';
  location: string;
  name: string;
  searchText: string;
}

export function toManualFintsSelection(manualName: string): BankSelectionOption {
  return {
    id: 'fints:manual',
    kind: 'fints-manual',
    location: 'fints',
    name: manualName,
    searchText: `${manualName} fints hbci manual`.toLocaleLowerCase(),
  };
}

export function toManifestSelection(manifest: BankManifest, manualName: string): BankSelectionOption {
  if (manifest.location === 'fints')
    return toManualFintsSelection(manualName);
  return {
    id: `connector:${manifest.location}`,
    kind: 'connector',
    location: manifest.location,
    name: manifest.displayName,
    searchText: `${manifest.displayName} ${manifest.location}`.toLocaleLowerCase(),
  };
}

export function toBankSelectionOptions(manifests: readonly BankManifest[], manualName: string): BankSelectionOption[] {
  const connectors: BankSelectionOption[] = manifests
    .filter(({ location }) => location !== 'fints')
    .map(manifest => toManifestSelection(manifest, manualName));
  const banks: BankSelectionOption[] = toFintsBankOptions().map(bank => ({
    bank,
    id: `fints:${bank.id}`,
    kind: 'fints',
    location: 'fints',
    name: bank.name,
    searchText: bank.searchText,
  }));

  return [...connectors, ...banks]
    .sort((left, right) => left.name.localeCompare(right.name, 'de'))
    .concat(toManualFintsSelection(manualName));
}
