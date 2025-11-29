import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import { api } from '@/modules/api/rotki-api';
import {
  type AddCalendarEventResponse,
  AddCalendarEventResponseSchema,
  type CalendarEvent,
  CalendarEventCollectionResponse,
  type CalendarEventPayload,
  type CalendarEventRequestPayload,
} from '@/types/history/calendar';
import { mapCollectionResponse } from '@/utils/collection';

interface UseCalendarApiReturn {
  fetchCalendarEvents: (filter: MaybeRef<CalendarEventRequestPayload>) => Promise<Collection<CalendarEvent>>;
  addCalendarEvent: (payload: CalendarEventPayload) => Promise<AddCalendarEventResponse>;
  editCalendarEvent: (payload: CalendarEvent) => Promise<AddCalendarEventResponse>;
  deleteCalendarEvent: (identifier: number) => Promise<boolean>;
}

export function useCalendarApi(): UseCalendarApiReturn {
  const fetchCalendarEvents = async (
    filter: MaybeRef<CalendarEventRequestPayload>,
  ): Promise<Collection<CalendarEvent>> => {
    const response = await api.post<Collection<CalendarEvent>>(
      '/calendar',
      get(filter),
    );

    return mapCollectionResponse(CalendarEventCollectionResponse.parse(response));
  };

  const addCalendarEvent = async (payload: CalendarEventPayload): Promise<AddCalendarEventResponse> => {
    const response = await api.put<AddCalendarEventResponse>('/calendar', payload);
    return AddCalendarEventResponseSchema.parse(response);
  };

  const editCalendarEvent = async (payload: CalendarEvent): Promise<AddCalendarEventResponse> => {
    const response = await api.patch<AddCalendarEventResponse>('/calendar', payload);
    return AddCalendarEventResponseSchema.parse(response);
  };

  const deleteCalendarEvent = async (identifier: number): Promise<boolean> => api.delete<boolean>('/calendar', {
    body: { identifier },
  });

  return {
    addCalendarEvent,
    deleteCalendarEvent,
    editCalendarEvent,
    fetchCalendarEvents,
  };
}
