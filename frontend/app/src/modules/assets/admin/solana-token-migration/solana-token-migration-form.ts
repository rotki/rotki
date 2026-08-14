import { isValidSolanaAddress } from '@rotki/common';
import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface SolanaTokenMigrationMessages {
  addressInvalid: string;
  addressMissing: string;
  decimalsMissing: string;
  tokenKindMissing: string;
}

/**
 * The address is checked for shape only once it holds something, so an empty field reports that it
 * is empty rather than that it is malformed, which is the order vuelidate reported them in.
 *
 * Decimals are a number, so the rule fires on a cleared field rather than on a zero: zero decimals
 * is a real token setting, and vuelidate's `required` accepted it too.
 */
export function solanaTokenMigrationSchema(messages: SolanaTokenMigrationMessages): ZodType {
  return z.object({
    address: requiredField(messages.addressMissing)
      .refine(value => value.trim() === '' || isValidSolanaAddress(value), messages.addressInvalid),
    decimals: z.number({ error: messages.decimalsMissing }),
    tokenKind: requiredField(messages.tokenKindMissing),
  }).passthrough();
}
