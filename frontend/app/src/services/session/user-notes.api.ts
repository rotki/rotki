import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';
import { Collection } from '@/types/collection';
import {
  UserNote,
  UserNoteCollectionResponse,
  UserNotesFilter
} from '@/types/notes';
import { mapCollectionResponse } from '@/utils/collection';

export const useUserNotesApi = () => {
  const fetchUserNotes = async (
    filter: UserNotesFilter
  ): Promise<Collection<UserNote>> => {
    const response = await api.instance.post<
      ActionResult<Collection<UserNote>>
    >('/notes', axiosSnakeCaseTransformer(filter));

    return mapCollectionResponse<UserNote>(
      UserNoteCollectionResponse.parse(handleResponse(response))
    );
  };

  const addUserNote = async (payload: Partial<UserNote>): Promise<number> => {
    const response = await api.instance.put<ActionResult<number>>(
      '/notes',
      axiosSnakeCaseTransformer(payload)
    );

    return handleResponse(response);
  };

  const updateUserNote = async (
    payload: Partial<UserNote>
  ): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/notes',
      axiosSnakeCaseTransformer(payload)
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
