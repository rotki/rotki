import type { ActionResult } from '@rotki/common';
import type { QueriedAddresses, QueriedAddressPayload } from '@/types/session';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus, validWithSessionStatus } from '@/services/utils';

interface UseQueriedAddressApiReturn {
  queriedAddresses: () => Promise<QueriedAddresses>;
  addQueriedAddress: (payload: QueriedAddressPayload) => Promise<QueriedAddresses>;
  deleteQueriedAddress: (payload: QueriedAddressPayload) => Promise<QueriedAddresses>;
}

export function useQueriedAddressApi(): UseQueriedAddressApiReturn {
  const queriedAddresses = async (): Promise<QueriedAddresses> => {
    const response = await api.instance.get<ActionResult<QueriedAddresses>>('/queried_addresses', {
      validateStatus: validWithSessionStatus,
    });

    return handleResponse(response);
  };

  const addQueriedAddress = async (payload: QueriedAddressPayload): Promise<QueriedAddresses> => {
    const response = await api.instance.put<ActionResult<QueriedAddresses>>('/queried_addresses', payload, {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const deleteQueriedAddress = async (payload: QueriedAddressPayload): Promise<QueriedAddresses> => {
    const response = await api.instance.delete<ActionResult<QueriedAddresses>>('/queried_addresses', {
      data: payload,
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  return {
    addQueriedAddress,
    deleteQueriedAddress,
    queriedAddresses,
  };
}
