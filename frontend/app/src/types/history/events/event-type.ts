import { HistoryEventEntryType } from '@rotki/common';
import { contextColors, RuiIcons } from '@rotki/ui-library';
import { z } from 'zod';

const HistoryEventTypeMapping = z.record(z.record(z.string()));

const RuiIcon = z.string().transform((icon) => {
  if (Array.prototype.includes.call(RuiIcons, icon))
    return icon satisfies RuiIcons;

  console.warn(`${icon} returned from the backend does not match RuiIcons`);
  return 'lu-circle-help' satisfies RuiIcons;
});

const HistoryEventTypeGlobalMapping = z.record(z.record(z.object({
  default: z.string(),
  exchange: z.string().optional(),
})));

const HistoryEventCategoryDetail = z.object({
  color: z.enum(contextColors).optional(),
  icon: RuiIcon,
  label: z.string(),
});

const HistoryEventCategoryDirection = z.enum(['neutral', 'in', 'out']);

const HistoryEventCategory = z.object({
  counterpartyMappings: z.record(HistoryEventCategoryDetail),
  direction: HistoryEventCategoryDirection,
});

export const HistoryEventCategoryDetailWithId = HistoryEventCategoryDetail.extend({
  direction: HistoryEventCategoryDirection,
  identifier: z.string(),
});

export type HistoryEventCategoryDetailWithId = z.infer<typeof HistoryEventCategoryDetailWithId>;

export const HistoryEventCategoryMapping = z.record(HistoryEventCategory);

export type HistoryEventCategoryMapping = z.infer<typeof HistoryEventCategoryMapping>;

export const HistoryEventTypeData = z.object({
  accountingEventsIcons: z.record(RuiIcon),
  entryTypeMappings: z.record(z.nativeEnum(HistoryEventEntryType), z.record(HistoryEventTypeMapping)),
  eventCategoryDetails: HistoryEventCategoryMapping,
  globalMappings: HistoryEventTypeGlobalMapping,
});

export type HistoryEventTypeData = z.infer<typeof HistoryEventTypeData>;

const HistoryEventProductMapping = z.array(z.string());

export const HistoryEventProductData = z.object({
  mappings: z.record(HistoryEventProductMapping),
  products: HistoryEventProductMapping,
});

export type HistoryEventProductData = z.infer<typeof HistoryEventProductData>;
