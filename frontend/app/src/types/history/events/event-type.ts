import { z } from 'zod';

const HistoryEventTypeMapping = z.record(z.record(z.string()));

const HistoryEventTypeDetail = z.object({
  label: z.string(),
  icon: z.string(),
  color: z.string().nullable()
});

const HistoryEventTypeDetails = z.record(HistoryEventTypeDetail);

export const HistoryEventTypeData = z.object({
  globalMappings: HistoryEventTypeMapping,
  perProtocolMappings: z.record(z.record(HistoryEventTypeMapping)),
  exchangeMappings: z.record(HistoryEventTypeMapping),
  eventCategoryDetails: HistoryEventTypeDetails,
  accountingEventsIcons: z.record(z.string())
});

export type HistoryEventTypeData = z.infer<typeof HistoryEventTypeData>;

const HistoryEventProductMapping = z.array(z.string());

export const HistoryEventProductData = z.object({
  mappings: z.record(HistoryEventProductMapping),
  products: HistoryEventProductMapping
});

export type HistoryEventProductData = z.infer<typeof HistoryEventProductData>;
