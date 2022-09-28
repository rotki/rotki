import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { SupportedAssets } from '@/services/types-api';
import {
  handleResponse,
  validWithSessionAndExternalService
} from '@/services/utils';
import { AssetPagination } from '@/types/assets';

export const useAssetManagementApi = () => {
  async function queryAllAssets(
    pagination: AssetPagination
  ): Promise<SupportedAssets> {
    const response = await api.instance.post<ActionResult<SupportedAssets>>(
      '/assets/all',
      axiosSnakeCaseTransformer(pagination),
      {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return SupportedAssets.parse(handleResponse(response));
  }

  return {
    queryAllAssets
  };
};
