import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import { api } from '@/modules/api/rotki-api';
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
    const response = await api.post<Collection<UserNote>>(
      '/notes',
      get(filter),
    );

    return mapCollectionResponse(UserNoteCollectionResponse.parse(response));
  };

  const addUserNote = async (payload: Partial<UserNote>): Promise<number> => api.put<number>('/notes', payload);

  const updateUserNote = async (payload: Partial<UserNote>): Promise<boolean> => api.patch<boolean>('/notes', payload);

  const deleteUserNote = async (identifier: number): Promise<boolean> => api.delete<boolean>('/notes', {
    body: {
      identifier,
    },
  });

  return {
    addUserNote,
    deleteUserNote,
    fetchUserNotes,
    updateUserNote,
  };
}
