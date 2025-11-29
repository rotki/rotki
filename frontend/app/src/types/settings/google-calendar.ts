import { z } from 'zod/v4';

export const GoogleCalendarStatusSchema = z.object({
  authenticated: z.boolean(),
  userEmail: z.string().optional(),
});

export type GoogleCalendarStatus = z.infer<typeof GoogleCalendarStatusSchema>;

export const GoogleCalendarAuthResultSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  userEmail: z.string().optional(),
});

export type GoogleCalendarAuthResult = z.infer<typeof GoogleCalendarAuthResultSchema>;

export const GoogleCalendarSyncResultSchema = z.object({
  success: z.boolean(),
  calendarId: z.string(),
  eventsProcessed: z.number(),
  eventsCreated: z.number(),
  eventsUpdated: z.number(),
});

export type GoogleCalendarSyncResult = z.infer<typeof GoogleCalendarSyncResultSchema>;

export const GoogleCalendarDisconnectResultSchema = z.object({
  success: z.boolean(),
});

export type GoogleCalendarDisconnectResult = z.infer<typeof GoogleCalendarDisconnectResultSchema>;
