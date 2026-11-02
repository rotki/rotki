import { z } from 'zod';
import catalog from '@/modules/banks/fints-bank-directory.json';

function isSafeEndpoint(value: string): boolean {
  const url = new URL(value);
  return url.protocol === 'https:' && url.username === '' && url.password === '';
}

const BankCodes = z.union([
  z.string().regex(/^\d{8}$/u),
  z.array(z.string().regex(/^\d{8}$/u)).min(2),
]);

const CompactFintsBank = z.tuple([
  z.string().min(1),
  z.string(),
  z.number().int().nonnegative(),
  BankCodes,
  z.array(z.string().min(1)).optional(),
]);

export const FintsBankDirectory = z.object({
  b: z.array(CompactFintsBank),
  e: z.array(z.url().refine(isSafeEndpoint)),
  h: z.string().regex(/^[a-f\d]{64}$/u),
  v: z.string().regex(/^\d{4}-\d{2}-\d{2}$/u),
}).superRefine(({ b: banks, e: endpoints }, ctx) => {
  const bankCodes = new Set<string>();
  banks.forEach(([, , endpointIndex, codes], index) => {
    if (endpoints[endpointIndex] === undefined)
      ctx.addIssue({ code: 'custom', message: `Unknown endpoint index ${endpointIndex}`, path: ['b', index, 2] });

    for (const bankCode of Array.isArray(codes) ? codes : [codes]) {
      if (bankCodes.has(bankCode))
        ctx.addIssue({ code: 'custom', message: `Duplicate BLZ ${bankCode}`, path: ['b', index, 3] });
      bankCodes.add(bankCode);
    }
  });
});

export type FintsBankDirectory = z.infer<typeof FintsBankDirectory>;

export interface FintsBank {
  aliases: string[];
  bankCodes: string[];
  city?: string;
  endpoint: string;
  id: string;
  name: string;
}

export interface FintsBankOption extends FintsBank {
  searchText: string;
}

export const fintsBankDirectory: FintsBankDirectory = FintsBankDirectory.parse(catalog);

function expandBank([name, city, endpointIndex, codes, aliases = []]: FintsBankDirectory['b'][number]): FintsBank {
  const bankCodes = Array.isArray(codes) ? codes : [codes];
  const endpoint = fintsBankDirectory.e[endpointIndex];
  if (endpoint === undefined)
    throw new Error(`FinTS catalog entry ${name} has no endpoint`);

  return {
    aliases,
    bankCodes,
    city: city || undefined,
    endpoint,
    id: bankCodes.join('-'),
    name,
  };
}

export const fintsBanks: FintsBank[] = fintsBankDirectory.b.map(expandBank);

function normalizeSearch(value: string): string {
  return value
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLocaleLowerCase();
}

function searchableText(bank: FintsBank): string {
  return normalizeSearch([bank.name, bank.city, ...bank.bankCodes, ...bank.aliases]
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
