import type { MaybeRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import {
  type AddCalendarEventResponse,
  AddCalendarEventResponseSchema,
  type CalendarEvent,
  CalendarEventCollectionResponse,
  type CalendarEventPayload,
  type CalendarEventRequestPayload,
} from '@/modules/calendar/types';
import { api } from '@/modules/core/api/rotki-api';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';

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
