import { z, type ZodType } from 'zod';
import { type AddressCheck, AddressVerdict } from '@/modules/accounts/blockchain/address-check';

/** The two fields the addresses are typed into, one of which is on screen at a time. */
export interface AddressFormState {
  address: string;
  userAddresses: string;
}

/** An extended public key is offered instead of an address, and the parent switches mode for it. */
export function isXpubPrefix(value: string): boolean {
  return value.startsWith('xpub') || value.startsWith('ypub') || value.startsWith('zpub');
}

/**
 * Reads a pasted or typed list into the addresses it names, separated by commas or newlines.
 *
 * A repeat is dropped case-insensitively, since the same address in a different case is the same
 * account, and the first spelling is the one kept: it is what the user wrote.
 */
export function parseAddressEntries(text: string): string[] {
  const seen = new Map<string, string>();

  for (const entry of text.split(/[\n,]+/)) {
    const address = entry.trim();
    if (address.length === 0)
      continue;

    const key = address.toLocaleLowerCase();
    if (!seen.has(key))
      seen.set(key, address);
  }

  return [...seen.values()];
}

/** Replaces the selected range, so pasting over a selection substitutes it rather than appending. */
export function replaceSelection(current: string, replacement: string, start: number, end: number): string {
  return current.slice(0, start) + replacement + current.slice(end);
}

/** What the entries are checked against, and how a refused batch is reported. */
export interface AddressEntryCheck {
  readonly check: AddressCheck;
  readonly message: (refused: readonly string[]) => string;
}

/**
 * One address or a list of them, never both: whichever field is on screen is the one that has to be
 * filled in, and the other is left alone rather than reported as missing behind the scenes.
 *
 * With an `entryCheck`, every entry the backend would refuse for its form is reported on that field
 * before anything is sent.
 */
export function addressEntrySchema(message: string, multiple: boolean, entryCheck?: AddressEntryCheck): ZodType {
  return z.object({
    address: z.string(),
    userAddresses: z.string(),
  }).superRefine((state, ctx) => {
    const field = multiple ? 'userAddresses' : 'address';
    const value = state[field].trim();

    if (value === '') {
      ctx.addIssue({ code: 'custom', message, path: [field] });
      return;
    }

    if (!entryCheck)
      return;

    const entries = multiple ? parseAddressEntries(value) : [value];
    const refused = entries.filter(entry => entryCheck.check(entry) === AddressVerdict.INVALID);
    if (refused.length > 0)
      ctx.addIssue({ code: 'custom', message: entryCheck.message(refused), path: [field] });
  });
}
