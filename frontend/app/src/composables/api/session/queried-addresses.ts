import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import {
  type QueriedAddressPayload,
  type QueriedAddresses
} from '@/types/session';

export const useQueriedAddressApi = () => {
  const queriedAddresses = async (): Promise<QueriedAddresses> => {
    const response = await api.instance.get<ActionResult<QueriedAddresses>>(
      '/queried_addresses',
      {
        validateStatus: validWithSessionStatus
      }
    );

    return handleResponse(response);
  };

  const addQueriedAddress = async (
    payload: QueriedAddressPayload
  ): Promise<QueriedAddresses> => {
    const response = await api.instance.put<ActionResult<QueriedAddresses>>(
      '/queried_addresses',
      payload,
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteQueriedAddress = async (
    payload: QueriedAddressPayload
  ): Promise<QueriedAddresses> => {
    const response = await api.instance.delete<ActionResult<QueriedAddresses>>(
      '/queried_addresses',
      {
        data: payload,
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    queriedAddresses,
    addQueriedAddress,
    deleteQueriedAddress
  };
};
