import { z, type ZodType } from 'zod';

/** The single field an explorer override holds; errors are reported under this path. */
export const EXPLORER_URL_FIELD = 'url';

export interface ExplorerUrlState {
  url: string;
}

export interface ExplorerUrlMessages {
  https: string;
  url: string;
}

/**
 * An empty value is accepted: emptying the field is how an override is cleared, so it must reach the
 * save path rather than being rejected as invalid.
 */
function isHttps(value: string): boolean {
  return value === '' || value.startsWith('https');
}

/** Vuelidate skipped its rules on blank input, and a whitespace-only url is not worth two messages. */
function isBlank(value: string): boolean {
  return value.trim() === '';
}

export function explorerUrlSchema(messages: ExplorerUrlMessages): ZodType {
  return z.object({
    url: z.string().superRefine((value, ctx) => {
      if (!isHttps(value))
        ctx.addIssue({ code: 'custom', message: messages.https });

      if (!isBlank(value) && !z.url().safeParse(value).success)
        ctx.addIssue({ code: 'custom', message: messages.url });
    }),
  });
}
