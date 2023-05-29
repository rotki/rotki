import { z } from 'zod';

export const HistoryEventTypeMapping = z.record(z.record(z.string()));

export type HistoryEventTypeMapping = z.infer<typeof HistoryEventTypeMapping>;

export const HistoryEventTypeDetail = z.object({
  label: z.string(),
  icon: z.string(),
  color: z.string().nullable()
});

export type HistoryEventTypeDetail = z.infer<typeof HistoryEventTypeDetail>;
export const HistoryEventTypeDetails = z.record(HistoryEventTypeDetail);

export const HistoryEventTypeData = z.object({
  globalMappings: HistoryEventTypeMapping,
  perProtocolMappings: z.record(z.record(HistoryEventTypeMapping)),
  exchangeMappings: z.record(HistoryEventTypeMapping),
  eventCategoryDetails: HistoryEventTypeDetails,
  accountingEventsIcons: z.record(z.string())
});

export type HistoryEventTypeData = z.infer<typeof HistoryEventTypeData>;

export const HistoryEventProductMapping = z.array(z.string());

export const HistoryEventProductData = z.object({
  mappings: z.record(HistoryEventProductMapping),
  products: HistoryEventProductMapping
});

export type HistoryEventProductData = z.infer<typeof HistoryEventProductData>;
