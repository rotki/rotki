import { z } from 'zod/v4';

export const CalenderReminderPayload = z.object({
  eventId: z.number(),
  secsBefore: z.number(),
});

export type CalenderReminderPayload = z.infer<typeof CalenderReminderPayload>;

export const CalendarReminderEntry = CalenderReminderPayload.extend({
  acknowledged: z.boolean(),
  identifier: z.number(),
});

export type CalendarReminderEntry = z.infer<typeof CalendarReminderEntry>;

export const CalendarReminderEntries = z.object({
  entries: z.array(CalendarReminderEntry),
});

export type CalendarReminderEntries = z.infer<typeof CalendarReminderEntries>;

export interface CalendarReminderRequestPayload {
  identifier: number;
}

export interface CalendarReminderTemporaryPayload {
  isTemporary: boolean;
  identifier: number;
  secsBefore: number;
}

export interface CalendarReminderAddResponse {
  success?: number[];
  failed?: number[];
}
