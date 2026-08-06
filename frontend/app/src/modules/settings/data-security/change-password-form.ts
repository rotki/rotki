import { z, type ZodType } from 'zod';

export interface ChangePasswordFormState {
  currentPassword: string;
  newPassword: string;
  newPasswordConfirm: string;
}

export interface ChangePasswordFormMessages {
  emptyPassword: string;
  emptyConfirmation: string;
  mismatch: string;
}

export function emptyChangePasswordState(): ChangePasswordFormState {
  return {
    currentPassword: '',
    newPassword: '',
    newPasswordConfirm: '',
  };
}

/** Whitespace-only counts as missing, as the rule this replaces did. */
function isEmpty(value: string): boolean {
  return value.trim() === '';
}

export function changePasswordSchema(messages: ChangePasswordFormMessages): ZodType {
  return z.object({
    currentPassword: z.string(),
    newPassword: z.string(),
    newPasswordConfirm: z.string(),
  }).superRefine((state, ctx) => {
    if (isEmpty(state.currentPassword))
      ctx.addIssue({ code: 'custom', message: messages.emptyPassword, path: ['currentPassword'] });

    if (isEmpty(state.newPassword))
      ctx.addIssue({ code: 'custom', message: messages.emptyPassword, path: ['newPassword'] });

    if (isEmpty(state.newPasswordConfirm))
      ctx.addIssue({ code: 'custom', message: messages.emptyConfirmation, path: ['newPasswordConfirm'] });

    // Reported independently of the rule above, as vuelidate did: a blank confirmation against a
    // filled new password is both empty and different, and both messages were shown.
    if (state.newPasswordConfirm !== state.newPassword)
      ctx.addIssue({ code: 'custom', message: messages.mismatch, path: ['newPasswordConfirm'] });
  });
}
