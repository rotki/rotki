import { z, type ZodType } from 'zod';
import { Constraints } from '@/modules/core/common/constraints';
import { numberSettingField } from '@/modules/settings/controls/setting-field-schemas';

export interface PasswordConfirmationFormState {
  /** Days, as typed. Converted to the seconds the setting stores only on save. */
  intervalDays: string;
}

export function toIntervalSeconds(intervalDays: string): number {
  return Math.round(Number.parseFloat(intervalDays) * Constraints.SECONDS_PER_DAY);
}

export function toIntervalDays(intervalSeconds: number): string {
  return String(intervalSeconds / Constraints.SECONDS_PER_DAY);
}

/**
 * The interval is only worth validating while the confirmation is on: a disabled setting is saved
 * with whatever is in the field, exactly as before.
 */
export function passwordConfirmationSchema(enabled: boolean, rangeMessage: string): ZodType {
  if (!enabled)
    return z.object({ intervalDays: z.string() });

  return z.object({
    intervalDays: numberSettingField({
      max: Constraints.MAX_PASSWORD_CONFIRMATION_DAYS,
      messages: { between: rangeMessage, required: rangeMessage },
      min: Constraints.MIN_PASSWORD_CONFIRMATION_DAYS,
      required: true,
    }),
  });
}
