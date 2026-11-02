import { z } from 'zod';
import catalog from '@/modules/banks/fints-bank-directory.json';

function isSafeEndpoint(value: string): boolean {
  const url = new URL(value);
  return url.protocol === 'https:' && url.username === '' && url.password === '';
}

export const FintsBank = z.object({
  aliases: z.array(z.string()),
  blz: z.string().regex(/^\d{8}$/u),
  city: z.string().optional(),
  endpoint: z.url().refine(isSafeEndpoint).optional(),
  name: z.string().min(1),
  source: z.url(),
});

export type FintsBank = z.infer<typeof FintsBank>;

export const FintsBankDirectory = z.object({
  banks: z.array(FintsBank),
  provenance: z.string().min(1),
  version: z.string().min(1),
}).superRefine(({ banks }, ctx) => {
  const bankCodes = new Set<string>();
  banks.forEach((bank, index) => {
    if (bankCodes.has(bank.blz))
      ctx.addIssue({ code: 'custom', message: `Duplicate BLZ ${bank.blz}`, path: ['banks', index, 'blz'] });

    bankCodes.add(bank.blz);
  });
});

export type FintsBankDirectory = z.infer<typeof FintsBankDirectory>;

export interface FintsBankOption extends FintsBank {
  searchText: string;
}

export const fintsBankDirectory: FintsBankDirectory = FintsBankDirectory.parse(catalog);

export const fintsBanks: FintsBank[] = fintsBankDirectory.banks;

function normalizeSearch(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase();
}

function searchableText(bank: FintsBank): string {
  return normalizeSearch([bank.name, bank.blz, bank.city, ...bank.aliases]
    .filter(isDefined)
    .join(' '));
}

export function toFintsBankOptions(banks: readonly FintsBank[] = fintsBanks): FintsBankOption[] {
  return banks.map(bank => ({ ...bank, searchText: searchableText(bank) }));
}

export function searchFintsBanks(query: string, banks: readonly FintsBank[] = fintsBanks): FintsBank[] {
  const terms = normalizeSearch(query).trim().split(/\s+/u);
  return banks.filter(bank => terms.every(term => searchableText(bank).includes(term)));
}
