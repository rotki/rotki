import type { PaginationRequestPayload } from '@/types/common';
import { z } from 'zod/v4';
import { CollectionCommonFields } from '@/types/collection';

export const CounterpartyMappingDeletePayload = z.object({
  counterparty: z.string(),
  counterpartySymbol: z.string(),
});

export type CounterpartyMappingDeletePayload = z.infer<typeof CounterpartyMappingDeletePayload>;

export const CounterpartyMapping = CounterpartyMappingDeletePayload.extend({
  asset: z.string(),
});

export type CounterpartyMapping = z.infer<typeof CounterpartyMapping>;

export interface CounterpartyMappingRequestPayload extends PaginationRequestPayload<CounterpartyMapping> {
  counterparty?: string;
}

export const CounterpartyMappingCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(CounterpartyMapping),
});
