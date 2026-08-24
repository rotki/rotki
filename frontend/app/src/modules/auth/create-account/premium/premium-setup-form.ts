import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface PremiumSetupMessages {
  apiKey: string;
  apiSecret: string;
}

/**
 * Whether premium is being set up at all is a choice the wizard step above owns, not part of the
 * payload, so it is a parameter here and the schema is rebuilt when it flips, rather than a rule
 * reaching back into form state.
 *
 * `syncDatabase` travels in the same payload but has never had a rule; it passes through untouched,
 * because giving a carried field a structural type is what once made a form unsaveable with nothing
 * on screen.
 */
export function premiumSetupSchema(messages: PremiumSetupMessages, enabled: boolean): ZodType {
  if (!enabled)
    return z.object({}).passthrough();

  return z.object({
    apiKey: requiredField(messages.apiKey),
    apiSecret: requiredField(messages.apiSecret),
  }).passthrough();
}
