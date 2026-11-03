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

/** A packaged logo file in the protocol images. */
const LogoFile = z.string().regex(/^bank_[\da-z_]+\.(?:png|svg)$/u);

export const FintsBankDirectory = z.object({
  b: z.array(CompactFintsBank),
  e: z.array(z.url().refine(isSafeEndpoint)),
  g: z.record(LogoFile, z.array(z.number().int().nonnegative())),
  h: z.string().regex(/^[a-f\d]{64}$/u),
  v: z.string().regex(/^\d{4}-\d{2}-\d{2}$/u),
}).superRefine(({ b: banks, e: endpoints, g: logos }, ctx) => {
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

  const withLogo = new Set<number>();
  for (const [logo, indices] of Object.entries(logos)) {
    for (const index of indices) {
      if (banks[index] === undefined || withLogo.has(index))
        ctx.addIssue({ code: 'custom', message: `Logo ${logo} names institution ${index} that is missing or has a logo`, path: ['g', logo] });
      withLogo.add(index);
    }
  }
});

export type FintsBankDirectory = z.infer<typeof FintsBankDirectory>;

export interface FintsBank {
  aliases: string[];
  bankCodes: string[];
  city?: string;
  endpoint: string;
  id: string;
  /** The bank's logo in the protocol images; a bank without one shows the generic bank icon. */
  logo?: string;
  name: string;
}

export interface FintsBankOption extends FintsBank {
  searchText: string;
}

export const fintsBankDirectory: FintsBankDirectory = FintsBankDirectory.parse(catalog);

const logoByBank = new Map<number, string>(Object.entries(fintsBankDirectory.g)
  .flatMap(([logo, indices]) => indices.map(index => [index, logo] as const)));

function expandBank([name, city, endpointIndex, codes, aliases = []]: FintsBankDirectory['b'][number], index: number): FintsBank {
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
    logo: logoByBank.get(index),
    name,
  };
}

export const fintsBanks: FintsBank[] = fintsBankDirectory.b.map(expandBank);

const logoByBankCode = new Map<string, string>(fintsBanks
  .flatMap(({ bankCodes, logo }) => (logo ? bankCodes.map(bankCode => [bankCode, logo] as const) : [])));

/** The logo of the bank with this code (BLZ), if the directory has one. */
export function fintsBankLogo(bankCode: string): string | undefined {
  return logoByBankCode.get(bankCode);
}

/** `value` lower-cased and without diacritics, so `Münster` matches `munster`. */
export function normalizeSearch(value: string): string {
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
