import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface CounterpartyMappingMessages {
  asset: string;
  counterparty: string;
  counterpartySymbol: string;
}

interface CounterpartyMappingState {
  asset: string;
  counterparty: string;
  counterpartySymbol: string;
}

/** Built per call: a zod builder is mutable, so a shared instance would leak between callers. */
export function counterpartyMappingSchema(
  messages: CounterpartyMappingMessages,
): ZodType<CounterpartyMappingState> {
  return z.object({
    asset: requiredField(messages.asset),
    counterparty: requiredField(messages.counterparty),
    counterpartySymbol: requiredField(messages.counterpartySymbol),
  });
}
