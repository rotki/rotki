import type { AddCalendarEventResponse } from '@/types/history/calendar';
import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';
import {
  type CalendarReminderAddResponse,
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
    const response = await api.instance.post<ActionResult<CalendarReminderEntries>>(
      '/calendar/reminders',
      snakeCaseTransformer(filter),
    );

    return CalendarReminderEntries.parse(handleResponse(response)).entries;
  };

  const addCalendarReminder = async (reminders: CalenderReminderPayload[]): Promise<CalendarReminderAddResponse> => {
    const response = await api.instance.put<ActionResult<CalendarReminderAddResponse>>(
      '/calendar/reminders',
      snakeCaseTransformer({
        reminders,
      }),
    );

    return handleResponse(response);
  };

  const editCalendarReminder = async (payload: CalendarReminderEntry): Promise<AddCalendarEventResponse> => {
    const response = await api.instance.patch<ActionResult<AddCalendarEventResponse>>(
      '/calendar/reminders',
      snakeCaseTransformer(payload),
    );

    return handleResponse(response);
  };

  const deleteCalendarReminder = async (identifier: number): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/calendar/reminders', {
      data: snakeCaseTransformer({ identifier }),
    });

    return handleResponse(response);
  };

  return {
    addCalendarReminder,
    deleteCalendarReminder,
    editCalendarReminder,
    fetchCalendarReminders,
  };
}
