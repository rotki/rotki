import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface ManualPriceMessages {
  fromAsset: string;
  price: string;
  toAsset: string;
}

export interface HistoricPriceMessages extends ManualPriceMessages {
  date: string;
}

interface ManualPriceFields {
  fromAsset: ZodType<string>;
  price: ZodType<string>;
  toAsset: ZodType<string>;
}

/** Built per call: a zod builder is mutable, so a shared instance would leak between callers. */
function manualPriceFields(messages: ManualPriceMessages): ManualPriceFields {
  return {
    fromAsset: requiredField(messages.fromAsset),
    price: requiredField(messages.price),
    toAsset: requiredField(messages.toAsset),
  };
}

export function latestPriceSchema(messages: ManualPriceMessages): ZodType {
  return z.object(manualPriceFields(messages));
}

/**
 * The same three fields plus the date. The timestamp is a number, so the rule it carries only fires
 * on a cleared picker - the epoch is a date like any other, which is what vuelidate's `required`
 * reported too. `sourceType` is carried for the payload and never edited here.
 */
export function historicPriceSchema(messages: HistoricPriceMessages): ZodType {
  return z.object({
    ...manualPriceFields(messages),
    sourceType: z.string(),
    timestamp: z.number({ error: messages.date }),
  });
}
