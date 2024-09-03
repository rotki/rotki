import { z } from 'zod';
import { RuiIcons, contextColors } from '@rotki/ui-library';
import { HistoryEventEntryType } from '@rotki/common';

const HistoryEventTypeMapping = z.record(z.record(z.string()));

const RuiIcon = z.string().transform((icon) => {
  if (Array.prototype.includes.call(RuiIcons, icon))
    return icon satisfies RuiIcons;

  console.warn(`${icon} returned from the backend does not match RuiIcons`);
  return 'question-line' satisfies RuiIcons;
});

const HistoryEventCategoryDetail = z.object({
  label: z.string(),
  icon: RuiIcon,
  color: z.enum(contextColors).optional(),
});

const HistoryEventCategoryDirection = z.enum(['neutral', 'in', 'out']);

const HistoryEventCategory = z.object({
  counterpartyMappings: z.record(HistoryEventCategoryDetail),
  direction: HistoryEventCategoryDirection,
});

export const HistoryEventCategoryDetailWithId = HistoryEventCategoryDetail.extend({
  identifier: z.string(),
  direction: HistoryEventCategoryDirection,
});

export type HistoryEventCategoryDetailWithId = z.infer<typeof HistoryEventCategoryDetailWithId>;

export const HistoryEventCategoryMapping = z.record(HistoryEventCategory);

export type HistoryEventCategoryMapping = z.infer<typeof HistoryEventCategoryMapping>;

export const HistoryEventTypeData = z.object({
  globalMappings: HistoryEventTypeMapping,
  eventCategoryDetails: HistoryEventCategoryMapping,
  accountingEventsIcons: z.record(RuiIcon),
  entryTypeMappings: z.record(z.nativeEnum(HistoryEventEntryType), z.record(HistoryEventTypeMapping)),
});

export type HistoryEventTypeData = z.infer<typeof HistoryEventTypeData>;

const HistoryEventProductMapping = z.array(z.string());

export const HistoryEventProductData = z.object({
  mappings: z.record(HistoryEventProductMapping),
  products: HistoryEventProductMapping,
});

export type HistoryEventProductData = z.infer<typeof HistoryEventProductData>;
