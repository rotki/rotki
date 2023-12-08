import { z } from 'zod';
import { contextColors } from '@rotki/ui-library-compat';

const HistoryEventTypeMapping = z.record(z.record(z.string()));

const HistoryEventCategoryDetail = z.object({
  label: z.string(),
  icon: z.string(),
  color: z.enum(contextColors).optional()
});

const HistoryEventCategoryDirection = z.enum(['neutral', 'in', 'out']);

const HistoryEventCategory = z.object({
  counterpartyMappings: z.record(HistoryEventCategoryDetail),
  direction: HistoryEventCategoryDirection
});

export const HistoryEventCategoryDetailWithId =
  HistoryEventCategoryDetail.extend({
    identifier: z.string(),
    direction: HistoryEventCategoryDirection
  });

export type HistoryEventCategoryDetailWithId = z.infer<
  typeof HistoryEventCategoryDetailWithId
>;

export const HistoryEventCategoryMapping = z.record(HistoryEventCategory);

export type HistoryEventCategoryMapping = z.infer<
  typeof HistoryEventCategoryMapping
>;

export const HistoryEventTypeData = z.object({
  globalMappings: HistoryEventTypeMapping,
  eventCategoryDetails: HistoryEventCategoryMapping,
  accountingEventsIcons: z.record(z.string())
});

export type HistoryEventTypeData = z.infer<typeof HistoryEventTypeData>;

const HistoryEventProductMapping = z.array(z.string());

export const HistoryEventProductData = z.object({
  mappings: z.record(HistoryEventProductMapping),
  products: HistoryEventProductMapping
});

export type HistoryEventProductData = z.infer<typeof HistoryEventProductData>;
