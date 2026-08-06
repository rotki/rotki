import { z, type ZodType } from 'zod';
import { isSingleVisualCharacter } from '@/modules/core/common/validation/validation';

/**
 * Both separators live in one state object so the "they must differ" rule can be a property of the
 * pair rather than of either field. Validating them separately is what let a rejected draft of one
 * field be used as the comparison value for the other, persisting two identical separators.
 */
export interface NumericSeparatorsState {
  thousand: string;
  decimal: string;
}

interface SeparatorMessages {
  /** Shown when the value is a digit. */
  numeric: string;
  empty: string;
  singleCharacter: string;
  /** Shown on BOTH fields: neither may persist while the pair is equal. */
  sameAsOther: string;
}

export interface NumericSeparatorsMessages {
  thousand: SeparatorMessages;
  decimal: SeparatorMessages;
}

/** Vuelidate's `numeric`: digits only. A separator may not be one. */
function isNumeric(value: string): boolean {
  return /^\d+$/.test(value);
}

/**
 * Issues for one separator, in the order the Vuelidate rules were declared, so a field that trips
 * several rules keeps reporting the same messages in the same order.
 */
function addFieldIssues(value: string, field: keyof NumericSeparatorsState, messages: SeparatorMessages, ctx: z.RefinementCtx): void {
  if (isNumeric(value))
    ctx.addIssue({ code: 'custom', message: messages.numeric, path: [field] });

  if (value.length === 0)
    ctx.addIssue({ code: 'custom', message: messages.empty, path: [field] });

  if (!isSingleVisualCharacter(value))
    ctx.addIssue({ code: 'custom', message: messages.singleCharacter, path: [field] });
}

export function numericSeparatorsSchema(messages: NumericSeparatorsMessages): ZodType {
  return z.object({
    decimal: z.string(),
    thousand: z.string(),
  }).superRefine((state, ctx) => {
    addFieldIssues(state.thousand, 'thousand', messages.thousand, ctx);
    addFieldIssues(state.decimal, 'decimal', messages.decimal, ctx);

    // The pair rule reports on both fields: the submit is all-or-nothing, so blaming only the field
    // that was last edited would leave the other looking persistable when it is not.
    if (state.thousand === state.decimal) {
      ctx.addIssue({ code: 'custom', message: messages.thousand.sameAsOther, path: ['thousand'] });
      ctx.addIssue({ code: 'custom', message: messages.decimal.sameAsOther, path: ['decimal'] });
    }
  });
}
