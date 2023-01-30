import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithoutSessionStatus
} from '@/services/utils';

export const useAssetIgnoreApi = () => {
  const getIgnoredAssets = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<string[]>>(
      '/assets/ignored',
      {
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  const addIgnoredAssets = async (assets: string[]): Promise<string[]> => {
    const response = await api.instance.put<ActionResult<string[]>>(
      '/assets/ignored',
      {
        assets
      },
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const removeIgnoredAssets = async (assets: string[]): Promise<string[]> => {
    const response = await api.instance.delete<ActionResult<string[]>>(
      '/assets/ignored',
      {
        data: {
          assets
        },
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    getIgnoredAssets,
    addIgnoredAssets,
    removeIgnoredAssets
  };
};
