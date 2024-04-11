import {
  type AddCalendarEventResponse,
  type CalendarEvent,
  CalendarEventCollectionResponse,
  type CalendarEventPayload,
  type CalendarEventRequestPayload,
} from '@/types/history/calendar';
import { api } from '@/services/rotkehlchen-api';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { handleResponse } from '@/services/utils';
import type { Collection } from '@/types/collection';
import type { MaybeRef } from '@vueuse/core';
import type { UserNote } from '@/types/notes';
import type { ActionResult } from '@rotki/common/lib/data';

export function useCalendarApi() {
  const fetchCalendarEvents = async (
    filter: MaybeRef<CalendarEventRequestPayload>,
  ): Promise<Collection<CalendarEvent>> => {
    const response = await api.instance.post<
        ActionResult<Collection<UserNote>>
    >('/calendar', snakeCaseTransformer(get(filter)));

    return mapCollectionResponse(
      CalendarEventCollectionResponse.parse(handleResponse(response)),
    );
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
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/calendar',
      {
        data: snakeCaseTransformer({ identifier }),
      },
    );

    return handleResponse(response);
  };

  return {
    fetchCalendarEvents,
    addCalendarEvent,
    editCalendarEvent,
    deleteCalendarEvent,
  };
}
