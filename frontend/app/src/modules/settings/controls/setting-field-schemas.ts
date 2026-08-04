import { z, type ZodType } from 'zod';

/**
 * The setting controls hold exactly one field, and both the baked schemas here and any schema a
 * caller passes in address it under this key.
 */
export const SETTING_FIELD = 'value';

/** The one field a setting control validates. Its input is always the raw string from the field. */
export interface SettingFieldState {
  value: string;
}

export interface TextSettingRules {
  required?: boolean;
  maxLength?: number;
  /**
   * Already-translated messages rather than i18n keys: the range messages interpolate their own
   * bounds, which a bare key cannot carry. The form core passes anything that is not a key through
   * untouched.
   */
  messages: {
    required?: string;
    maxLength?: string;
  };
}

export interface NumberSettingRules {
  required?: boolean;
  min?: number;
  max?: number;
  /** See `TextSettingRules.messages`. `between` is used when both bounds are given. */
  messages: {
    required?: string;
    min?: string;
    max?: string;
    between?: string;
  };
}

/** Vuelidate treats a whitespace-only string as empty; keep that so nothing changes under the user. */
function isBlank(value: string): boolean {
  return value.trim() === '';
}

export function textSettingSchema(rules: TextSettingRules): ZodType {
  const { maxLength, messages, required = false } = rules;

  return z.object({
    value: z.string().superRefine((value, ctx) => {
      if (isBlank(value)) {
        // A blank value is the required rule's business alone: an optional field that is empty must
        // not also trip the length rule.
        if (required)
          ctx.addIssue({ code: 'custom', message: messages.required });

        return;
      }

      if (maxLength !== undefined && value.length > maxLength)
        ctx.addIssue({ code: 'custom', message: messages.maxLength });
    }),
  });
}

/**
 * The message for a value that is outside its bounds, or `undefined` when it is within them. Two
 * bounds report one `between` message rather than a separate min and max.
 */
function rangeMessage(numeric: number, rules: NumberSettingRules): string | undefined {
  const { max, messages, min } = rules;

  if (min !== undefined && max !== undefined)
    return numeric < min || numeric > max ? messages.between : undefined;

  if (min !== undefined)
    return numeric < min ? messages.min : undefined;

  if (max !== undefined)
    return numeric > max ? messages.max : undefined;

  return undefined;
}

export function numberSettingSchema(rules: NumberSettingRules): ZodType {
  const { messages, required = true } = rules;

  return z.object({
    value: z.string().superRefine((value, ctx) => {
      if (isBlank(value)) {
        if (required)
          ctx.addIssue({ code: 'custom', message: messages.required });

        return;
      }

      const numeric = Number(value);
      if (Number.isNaN(numeric)) {
        ctx.addIssue({ code: 'custom', message: messages.required });
        return;
      }

      const message = rangeMessage(numeric, rules);
      if (message !== undefined)
        ctx.addIssue({ code: 'custom', message });
    }),
  });
}
