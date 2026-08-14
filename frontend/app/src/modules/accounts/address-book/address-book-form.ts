import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface AddressBookFormMessages {
  address: string;
  chain: string;
  name: string;
}

/**
 * The chain is held as null for "every chain", so it needs the nullable twin of `requiredField`:
 * the old rule rejected null and whitespace alike, under the one message.
 */
function requiredChain(message: string): ZodType {
  return z.string({ error: message }).nullable().superRefine((value, ctx) => {
    if ((value ?? '').trim() === '')
      ctx.addIssue({ code: 'custom', message });
  });
}

/**
 * The location is deliberately absent: it picks which book the entry is written to rather than
 * describing the entry, and it was never validated. Zod drops the keys a schema does not name, so
 * it travels untouched.
 */
export function addressBookEntrySchema(messages: AddressBookFormMessages): ZodType {
  return z.object({
    address: requiredField(messages.address),
    blockchain: requiredChain(messages.chain),
    name: requiredField(messages.name),
  });
}
