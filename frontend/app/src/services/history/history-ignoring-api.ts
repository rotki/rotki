import { ActionResult } from '@rotki/common/lib/data';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { IgnoreActionType } from '@/store/history/types';
import { IgnoredActions } from '@/types/history/ignored';

export const useHistoryIgnoringApi = () => {
  const fetchIgnored = async (): Promise<IgnoredActions> => {
    return api.instance
      .get<ActionResult<IgnoredActions>>('/actions/ignored', {
        validateStatus: validStatus,
        transformResponse: setupTransformer([])
      })
      .then(handleResponse)
      .then(result => IgnoredActions.parse(result));
  };

  const ignoreActions = async (
    actionIds: string[],
    actionType: IgnoreActionType
  ): Promise<IgnoredActions> => {
    const response = await api.instance.put<ActionResult<IgnoredActions>>(
      '/actions/ignored',
      axiosSnakeCaseTransformer({
        actionIds,
        actionType
      }),
      {
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return IgnoredActions.parse(handleResponse(response));
  };

  const unignoreActions = async (
    actionIds: string[],
    actionType: IgnoreActionType
  ): Promise<IgnoredActions> => {
    const response = await api.instance.delete<ActionResult<IgnoredActions>>(
      '/actions/ignored',
      {
        data: axiosSnakeCaseTransformer({
          actionIds,
          actionType
        }),
        validateStatus: validStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return IgnoredActions.parse(handleResponse(response));
  };

  return {
    fetchIgnored,
    ignoreActions,
    unignoreActions
  };
};
