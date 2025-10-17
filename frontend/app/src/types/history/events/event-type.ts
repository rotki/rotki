import { HistoryEventEntryType } from '@rotki/common';
import { contextColors, RuiIcons } from '@rotki/ui-library';
import { z } from 'zod/v4';

const HistoryEventTypeMapping = z.record(z.string(), z.record(z.string(), z.string()));

const RuiIcon = z.string().transform((icon) => {
  if (Array.prototype.includes.call(RuiIcons, icon))
    return icon satisfies RuiIcons;

  console.warn(`${icon} returned from the backend does not match RuiIcons`);
  return 'lu-circle-question-mark' satisfies RuiIcons;
});

const HistoryEventTypeGlobalMapping = z.record(z.string(), z.record(z.string(), z.object({
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
  counterpartyMappings: z.record(z.string(), HistoryEventCategoryDetail),
  direction: HistoryEventCategoryDirection,
});

export const HistoryEventCategoryDetailWithId = HistoryEventCategoryDetail.extend({
  direction: HistoryEventCategoryDirection,
  identifier: z.string(),
});

export type HistoryEventCategoryDetailWithId = z.infer<typeof HistoryEventCategoryDetailWithId>;

export const HistoryEventCategoryMapping = z.record(z.string(), HistoryEventCategory);

export type HistoryEventCategoryMapping = z.infer<typeof HistoryEventCategoryMapping>;

export const HistoryEventTypeData = z.object({
  accountingEventsIcons: z.record(z.string(), RuiIcon),
  entryTypeMappings: z.partialRecord(z.enum(HistoryEventEntryType), z.record(z.string(), HistoryEventTypeMapping)),
  eventCategoryDetails: HistoryEventCategoryMapping,
  globalMappings: HistoryEventTypeGlobalMapping,
});

export type HistoryEventTypeData = z.infer<typeof HistoryEventTypeData>;
