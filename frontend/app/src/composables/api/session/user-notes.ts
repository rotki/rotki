import { type ActionResult } from '@rotki/common/lib/data';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';
import { type Collection } from '@/types/collection';
import {
  type UserNote,
  UserNoteCollectionResponse,
  type UserNotesFilter
} from '@/types/notes';

export const useUserNotesApi = () => {
  const fetchUserNotes = async (
    filter: UserNotesFilter
  ): Promise<Collection<UserNote>> => {
    const response = await api.instance.post<
      ActionResult<Collection<UserNote>>
    >('/notes', snakeCaseTransformer(filter));

    return mapCollectionResponse(
      UserNoteCollectionResponse.parse(handleResponse(response))
    );
  };

  const addUserNote = async (payload: Partial<UserNote>): Promise<number> => {
    const response = await api.instance.put<ActionResult<number>>(
      '/notes',
      snakeCaseTransformer(payload)
    );

    return handleResponse(response);
  };

  const updateUserNote = async (
    payload: Partial<UserNote>
  ): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/notes',
      snakeCaseTransformer(payload)
    );

    return handleResponse(response);
  };

  const deleteUserNote = async (identifier: number): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/notes',
      {
        data: {
          identifier
        }
      }
    );

    return handleResponse(response);
  };

  return {
    fetchUserNotes,
    addUserNote,
    updateUserNote,
    deleteUserNote
  };
};
