import { z, type ZodType } from 'zod';
import { usernameField } from '@/modules/auth/credentials-fields';
import { requiredField } from '@/modules/core/form/fields';

/**
 * What the form validates, which is wider than the credentials it contributes to: the confirmation
 * is never sent, and the backup prompt is a consent tick rather than a value.
 */
export interface CredentialsFormState {
  password: string;
  passwordConfirm: string;
  userPrompted: boolean;
  username: string;
}

export interface CredentialsFormMessages {
  confirmationMismatch: string;
  emptyConfirmation: string;
  emptyPassword: string;
  invalidUsername: string;
  prompt: string;
  requiredUsername: string;
}

/**
 * Both of the confirmation's rules sit on the object rather than on the field, so the comparison can
 * read the password without the schema depending on the state it is validating. Their order is the
 * order vuelidate declared them in, mismatch before missing, which a cleared confirmation reports
 * both of.
 */
function confirmationIssues(state: CredentialsFormState, messages: CredentialsFormMessages, ctx: z.RefinementCtx): void {
  if (state.passwordConfirm !== state.password)
    ctx.addIssue({ code: 'custom', message: messages.confirmationMismatch, path: ['passwordConfirm'] });

  if (state.passwordConfirm.trim() === '')
    ctx.addIssue({ code: 'custom', message: messages.emptyConfirmation, path: ['passwordConfirm'] });
}

export function credentialsSchema(messages: CredentialsFormMessages): ZodType {
  return z.object({
    password: requiredField(messages.emptyPassword),
    passwordConfirm: z.string(),
    userPrompted: z.boolean().superRefine((value, ctx) => {
      if (!value)
        ctx.addIssue({ code: 'custom', message: messages.prompt });
    }),
    username: usernameField({ invalid: messages.invalidUsername, required: messages.requiredUsername }),
  }).superRefine((state, ctx) => {
    confirmationIssues(state, messages, ctx);
  });
}
