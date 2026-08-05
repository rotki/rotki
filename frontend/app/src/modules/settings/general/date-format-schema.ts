import { z, type ZodType } from 'zod';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';

export interface DateFormatMessages {
  /** The pattern holds no directive the formatter understands. */
  invalid: string;
  empty: string;
}

/**
 * Schema for a date format pattern, addressing the value under the setting-control field key. Shared
 * by the display and the input format settings, which validate identically.
 *
 * A blank pattern reports both messages, as it holds no valid directive either.
 */
export function dateFormatSchema(messages: DateFormatMessages): ZodType {
  return z.object({
    value: z.string().superRefine((value, ctx) => {
      if (!displayDateFormatter.containsValidDirectives(value))
        ctx.addIssue({ code: 'custom', message: messages.invalid });

      if (value.length === 0)
        ctx.addIssue({ code: 'custom', message: messages.empty });
    }),
  });
}
