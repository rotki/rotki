import { z, type ZodType } from 'zod';

/**
 * A field that must hold something. Vuelidate's `required` treated a whitespace-only string as
 * empty and reported a missing value under the same message as a wrong-typed one, so both are kept.
 */
export function requiredField(message: string): ZodType<string> {
  return z.string({ error: message }).superRefine((value, ctx) => {
    if (value.trim() === '')
      ctx.addIssue({ code: 'custom', message });
  });
}
