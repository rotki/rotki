import { z, type ZodType } from 'zod';
import { msg } from '@/message-key';

export interface PremiumCredentialsFormState {
  apiKey: string;
  apiSecret: string;
}

export function emptyPremiumCredentialsForm(): PremiumCredentialsFormState {
  return { apiKey: '', apiSecret: '' };
}

/**
 * Both halves of the key pair are required. The inputs trim as the user types, so a whitespace only
 * value reaches the schema as `''` and is rejected the same way a blank one is.
 */
export function premiumCredentialsSchema(): ZodType<PremiumCredentialsFormState> {
  return z.object({
    apiKey: z.string().min(1, msg.$t('premium_settings.validation.api_key.non_empty')),
    apiSecret: z.string().min(1, msg.$t('premium_settings.validation.api_secret.non_empty')),
  });
}
