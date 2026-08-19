import type { BalanceType } from '@/modules/balances/types/balances';
import type { ManualBalance, RawManualBalance } from '@/modules/balances/types/manual-balances';
import { bigNumberify } from '@rotki/common';
import { z, type ZodType } from 'zod';
import { parseNumericInput } from '@/modules/core/common/data/bignumbers';
import { requiredField } from '@/modules/core/form/fields';

/**
 * What the form edits. The amount is text while it is being typed, and the tags are a plain list,
 * where the payload holds a number and uses null for "no tags".
 */
export interface ManualBalanceFormState {
  amount: string;
  asset: string;
  balanceType: BalanceType;
  label: string;
  location: string;
  tags: string[];
}

export function toFormState(balance: RawManualBalance | ManualBalance): ManualBalanceFormState {
  const { amount, asset, balanceType, label, location, tags } = balance;
  return {
    amount: !amount || amount.isNaN() ? '' : amount.toString(),
    asset,
    balanceType,
    label,
    location,
    tags: tags ?? [],
  };
}

/**
 * The round trip has to be lossless, or an edit written back would be read straight back in as a
 * different value: a cleared amount becomes NaN rather than zero precisely so that reading it
 * returns the empty field the user left, instead of refilling it with a nought they never typed.
 * An amount in that state never reaches the api, because the dialog saves only what validates.
 *
 * A field holding something that is not a number yet lands in the same state, rather than in the
 * throw a bare parse would raise on it.
 */
export function toPayload<T extends RawManualBalance>(balance: T, state: ManualBalanceFormState): T {
  return {
    ...balance,
    ...state,
    amount: parseNumericInput(state.amount, bigNumberify(Number.NaN)),
    tags: state.tags.length > 0 ? state.tags : null,
  };
}

export interface ManualBalanceMessages {
  amount: string;
  asset: string;
  labelEmpty: string;
  labelExists: (label: string) => string;
  location: string;
}

export interface ManualBalanceOptions {
  /** An existing balance keeps its own label, so uniqueness is not checked at all while editing. */
  readonly editing: boolean;
  /** The labels the other manual balances already use. */
  readonly takenLabels: string[];
}

export function manualBalanceSchema(messages: ManualBalanceMessages, options: ManualBalanceOptions): ZodType {
  const { editing, takenLabels } = options;

  return z.object({
    amount: requiredField(messages.amount),
    asset: requiredField(messages.asset),
    label: z.string().superRefine((label, ctx) => {
      // Reported in the order the rules were declared: uniqueness first, then presence. The
      // uniqueness check reads the label untrimmed, as it is compared against stored ones.
      if (!editing && takenLabels.includes(label))
        ctx.addIssue({ code: 'custom', message: messages.labelExists(label) });

      if (label.trim() === '')
        ctx.addIssue({ code: 'custom', message: messages.labelEmpty });
    }),
    location: requiredField(messages.location),
  });
}
