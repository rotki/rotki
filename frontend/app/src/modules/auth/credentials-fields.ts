import { z, type ZodType } from 'zod';

export interface UsernameMessages {
  /** Shown when the name holds anything outside the allowed set. */
  invalid: string;
  /** Shown when the name is missing. */
  required: string;
}

/** The character set the backend accepts for a user directory name. */
const USERNAME_PATTERN = /^[\w.-]+$/;

/**
 * Shared by the login form and the create-account form, which had the same regex written out twice
 * with different message keys. Keeping one copy matters beyond tidiness: were the two to drift, the
 * wizard would happily create an account that the login form then refuses to accept.
 *
 * Both rules report, and the format one reports first, because vuelidate evaluated every rule and
 * listed them in declaration order. An empty name therefore says both things, as it always has.
 */
export function usernameField(messages: UsernameMessages): ZodType<string> {
  return z.string({ error: messages.required }).superRefine((value, ctx) => {
    if (!USERNAME_PATTERN.test(value))
      ctx.addIssue({ code: 'custom', message: messages.invalid });

    if (value.trim() === '')
      ctx.addIssue({ code: 'custom', message: messages.required });
  });
}
