import type { ActionResult } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';
import { type UserNote, UserNoteCollectionResponse, type UserNotesRequestPayload } from '@/types/notes';
import { mapCollectionResponse } from '@/utils/collection';

interface UseUserNotesApiReturn {
  fetchUserNotes: (filter: MaybeRef<UserNotesRequestPayload>) => Promise<Collection<UserNote>>;
  addUserNote: (payload: Partial<UserNote>) => Promise<number>;
  updateUserNote: (payload: Partial<UserNote>) => Promise<boolean>;
  deleteUserNote: (identifier: number) => Promise<boolean>;
}

export function useUserNotesApi(): UseUserNotesApiReturn {
  const fetchUserNotes = async (filter: MaybeRef<UserNotesRequestPayload>): Promise<Collection<UserNote>> => {
    const response = await api.instance.post<ActionResult<Collection<UserNote>>>(
      '/notes',
      snakeCaseTransformer(get(filter)),
    );

    return mapCollectionResponse(UserNoteCollectionResponse.parse(handleResponse(response)));
  };

  const addUserNote = async (payload: Partial<UserNote>): Promise<number> => {
    const response = await api.instance.put<ActionResult<number>>('/notes', snakeCaseTransformer({
      ...payload,
      location: null,
    }));

    return handleResponse(response);
  };

  const updateUserNote = async (payload: Partial<UserNote>): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>('/notes', snakeCaseTransformer(payload));

    return handleResponse(response);
  };

  const deleteUserNote = async (identifier: number): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/notes', {
      data: {
        identifier,
      },
    });

    return handleResponse(response);
  };

  return {
    addUserNote,
    deleteUserNote,
    fetchUserNotes,
    updateUserNote,
  };
}
