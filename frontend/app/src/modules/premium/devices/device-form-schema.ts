import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface DeviceNameMessages {
  /** The name is blank. */
  required: string;
  /** The name is the one the device already carries, so renaming would be a no-op. */
  notEqual: string;
}

/** The state the rename form edits. The dialog owns it as a bare string. */
export interface DeviceNameState {
  deviceName: string;
}

/**
 * Schema for the device rename field.
 *
 * `currentName` is read once, by the caller, and passed in: vuelidate's `not(sameAs(...))` snapshotted
 * the prop at setup, so a device renamed underneath an open dialog kept being compared against the
 * name it had when the dialog opened. That is preserved rather than fixed, since making it reactive
 * would change which values a mounted form accepts.
 *
 * The no-op check skips a blank name, as vuelidate's `not` did through its `req` guard, so an empty
 * field reports only the missing-value message.
 */
export function deviceNameSchema(currentName: string, messages: DeviceNameMessages): ZodType {
  return z.object({
    deviceName: requiredField(messages.required).superRefine((value, ctx) => {
      if (value !== '' && value === currentName)
        ctx.addIssue({ code: 'custom', message: messages.notEqual });
    }),
  });
}
