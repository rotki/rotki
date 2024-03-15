import { omit } from 'lodash-es';
import {
  type CexMapping,
  CexMappingCollectionResponse,
  type CexMappingDeletePayload,
  type CexMappingRequestPayload,
  type SupportedAssets,
} from '@/types/asset';
import { api } from '@/services/rotkehlchen-api';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { handleResponse, validStatus } from '@/services/utils';
import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import type { ActionResult } from '@rotki/common/lib/data';

export function useAssetCexMappingApi() {
  const fetchAllCexMapping = async (
    payload: MaybeRef<CexMappingRequestPayload>,
  ): Promise<Collection<CexMapping>> => {
    const response = await api.instance.post<ActionResult<SupportedAssets>>(
      '/assets/locationmappings',
      snakeCaseTransformer(omit(get(payload), ['orderByAttributes', 'ascending'])),
      {
        validateStatus: validStatus,
      },
    );

    return mapCollectionResponse(
      CexMappingCollectionResponse.parse(handleResponse(response)),
    );
  };

  const addCexMapping = async (
    payload: CexMapping,
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/assets/locationmappings',
      snakeCaseTransformer({
        entries: [payload],
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const editCexMapping = async (
    payload: CexMapping,
  ): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/assets/locationmappings',
      snakeCaseTransformer({
        entries: [payload],
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const deleteCexMapping = async (
    payload: CexMappingDeletePayload,
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/assets/locationmappings',
      {
        data: snakeCaseTransformer({
          entries: [payload],
        }),
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  return {
    fetchAllCexMapping,
    addCexMapping,
    editCexMapping,
    deleteCexMapping,
  };
}
