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
  eventCategoryDetails: HistoryEventTypeDetails
});

export type HistoryEventTypeData = z.infer<typeof HistoryEventTypeData>;
