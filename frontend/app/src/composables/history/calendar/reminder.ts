import { api } from '@/modules/api/rotki-api';
import { type AddCalendarEventResponse, AddCalendarEventResponseSchema } from '@/types/history/calendar';
import {
  type CalendarReminderAddResponse,
  CalendarReminderAddResponseSchema,
  CalendarReminderEntries,
  type CalendarReminderEntry,
  type CalendarReminderRequestPayload,
  type CalenderReminderPayload,
} from '@/types/history/calendar/reminder';

interface UseCalendarReminderApi {
  fetchCalendarReminders: (filter: CalendarReminderRequestPayload) => Promise<CalendarReminderEntry[]>;
  addCalendarReminder: (reminders: CalenderReminderPayload[]) => Promise<CalendarReminderAddResponse>;
  editCalendarReminder: (payload: CalendarReminderEntry) => Promise<AddCalendarEventResponse>;
  deleteCalendarReminder: (identifier: number) => Promise<boolean>;
}

export function useCalendarReminderApi(): UseCalendarReminderApi {
  const fetchCalendarReminders = async (filter: CalendarReminderRequestPayload): Promise<CalendarReminderEntry[]> => {
    const response = await api.post<CalendarReminderEntries>(
      '/calendar/reminders',
      filter,
    );

    return CalendarReminderEntries.parse(response).entries;
  };

  const addCalendarReminder = async (reminders: CalenderReminderPayload[]): Promise<CalendarReminderAddResponse> => {
    const response = await api.put<CalendarReminderAddResponse>('/calendar/reminders', { reminders });
    return CalendarReminderAddResponseSchema.parse(response);
  };

  const editCalendarReminder = async (payload: CalendarReminderEntry): Promise<AddCalendarEventResponse> => {
    const response = await api.patch<AddCalendarEventResponse>('/calendar/reminders', payload);
    return AddCalendarEventResponseSchema.parse(response);
  };

  const deleteCalendarReminder = async (identifier: number): Promise<boolean> => api.delete<boolean>('/calendar/reminders', {
    body: { identifier },
  });

  return {
    addCalendarReminder,
    deleteCalendarReminder,
    editCalendarReminder,
    fetchCalendarReminders,
  };
}
