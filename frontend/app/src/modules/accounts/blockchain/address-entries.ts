import { z, type ZodType } from 'zod';

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

/**
 * One address or a list of them, never both: whichever field is on screen is the one that has to be
 * filled in, and the other is left alone rather than reported as missing behind the scenes.
 */
export function addressEntrySchema(message: string, multiple: boolean): ZodType {
  return z.object({
    address: z.string(),
    userAddresses: z.string(),
  }).superRefine((state, ctx) => {
    const field = multiple ? 'userAddresses' : 'address';

    if (state[field].trim() === '')
      ctx.addIssue({ code: 'custom', message, path: [field] });
  });
}
