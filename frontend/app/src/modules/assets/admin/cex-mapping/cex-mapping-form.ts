import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface CexMappingMessages {
  asset: string;
  location: string;
  locationSymbol: string;
}

/** Null is what "every exchange" means in this payload, so the field is nullable either way. */
function locationField(message: string, required: boolean): ZodType<string | null> {
  return z.string().nullable().superRefine((value, ctx) => {
    if (required && (value === null || value.trim() === ''))
      ctx.addIssue({ code: 'custom', message });
  });
}

/**
 * The exchange is required only while the mapping covers a single one, which the switch above the
 * field decides. That switch is not part of the payload, so the condition is passed in and the
 * schema is rebuilt when it flips, rather than the rule reaching back into form state.
 */
export function cexMappingSchema(
  messages: CexMappingMessages,
  forAllExchanges: boolean,
): ZodType {
  return z.object({
    asset: requiredField(messages.asset),
    location: locationField(messages.location, !forAllExchanges),
    locationSymbol: requiredField(messages.locationSymbol),
  }).passthrough();
}
