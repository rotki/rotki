import type { MaybeRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import { api } from '@/modules/core/api/rotki-api';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { type UserNote, UserNoteCollectionResponse, type UserNotesRequestPayload } from '@/modules/core/common/notes';

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
