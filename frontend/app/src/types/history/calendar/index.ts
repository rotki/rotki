import { z } from 'zod';
import { CollectionCommonFields } from '@/types/collection';
import type { PaginationRequestPayload } from '@/types/common';

export const CalendarEventPayload = z.object({
  address: z.string().optional(),
  autoDelete: z.boolean(),
  blockchain: z.string().optional(),
  color: z.string().optional(),
  counterparty: z.string().optional(),
  description: z.string(),
  name: z.string(),
  timestamp: z.number(),
});

export type CalendarEventPayload = z.infer<typeof CalendarEventPayload>;

export const CalendarEvent = CalendarEventPayload.extend({
  identifier: z.number(),
});

export type CalendarEvent = z.infer<typeof CalendarEvent>;

export const CalendarAccountFilter = z.object({
  address: z.string(),
  blockchain: z.string().optional(),
});

type CalendarAccountFilter = z.infer<typeof CalendarAccountFilter>;

export interface CalendarEventRequestPayload extends PaginationRequestPayload<CalendarEvent> {
  fromTimestamp?: number;
  toTimestamp?: number;
  accounts?: CalendarAccountFilter[];
  counterparty?: string;
}

export const CalendarEventCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(CalendarEvent),
});

export interface AddCalendarEventResponse {
  entryId: number;
}
