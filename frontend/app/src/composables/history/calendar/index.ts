import type { ActionResult } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';
import {
  type AddCalendarEventResponse,
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
    const response = await api.instance.post<ActionResult<Collection<CalendarEvent>>>(
      '/calendar',
      snakeCaseTransformer(get(filter)),
    );

    return mapCollectionResponse(CalendarEventCollectionResponse.parse(handleResponse(response)));
  };

  const addCalendarEvent = async (payload: CalendarEventPayload): Promise<AddCalendarEventResponse> => {
    const response = await api.instance.put<ActionResult<AddCalendarEventResponse>>(
      '/calendar',
      snakeCaseTransformer(payload),
    );

    return handleResponse(response);
  };

  const editCalendarEvent = async (payload: CalendarEvent): Promise<AddCalendarEventResponse> => {
    const response = await api.instance.patch<ActionResult<AddCalendarEventResponse>>(
      '/calendar',
      snakeCaseTransformer(payload),
    );

    return handleResponse(response);
  };

  const deleteCalendarEvent = async (identifier: number): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/calendar', {
      data: snakeCaseTransformer({ identifier }),
    });

    return handleResponse(response);
  };

  return {
    addCalendarEvent,
    deleteCalendarEvent,
    editCalendarEvent,
    fetchCalendarEvents,
  };
}
