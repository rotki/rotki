import { isValidTxHashOrSignature } from '@rotki/common';
import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

/** The payload's own fields are readonly, and the form has to be able to write them. */
export interface TransactionFormState {
  associatedAddress: string;
  blockchain: string;
  txRef: string;
}

export interface TransactionFormMessages {
  accountRequired: string;
  chainRequired: string;
  txRefRequired: string;
  txRefValid: string;
}

export function transactionFormSchema(messages: TransactionFormMessages): ZodType {
  return z.object({
    /*
     * Not trimmed, unlike the other two. The address is picked from a selector rather than typed,
     * so the rule only ever separates "an account is chosen" from "none is", and trimming here
     * would be a new rule rather than a port of the old one.
     */
    associatedAddress: z.string().min(1, { error: messages.accountRequired }),
    blockchain: requiredField(messages.chainRequired),
    /*
     * Both messages, because the format check runs on an empty string too and reports alongside
     * the missing-value one, which is what the form showed before.
     */
    txRef: requiredField(messages.txRefRequired).refine(isValidTxHashOrSignature, {
      error: messages.txRefValid,
    }),
  });
}
