import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import { type QueriedAddresses, QueriedAddressesSchema, type QueriedAddressPayload } from '@/types/session';

interface UseQueriedAddressApiReturn {
  queriedAddresses: () => Promise<QueriedAddresses>;
  addQueriedAddress: (payload: QueriedAddressPayload) => Promise<QueriedAddresses>;
  deleteQueriedAddress: (payload: QueriedAddressPayload) => Promise<QueriedAddresses>;
}

export function useQueriedAddressApi(): UseQueriedAddressApiReturn {
  const queriedAddresses = async (): Promise<QueriedAddresses> => {
    const response = await api.get<QueriedAddresses>('/queried_addresses', {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });
    return QueriedAddressesSchema.parse(response);
  };

  const addQueriedAddress = async (payload: QueriedAddressPayload): Promise<QueriedAddresses> => {
    const response = await api.put<QueriedAddresses>('/queried_addresses', payload);
    return QueriedAddressesSchema.parse(response);
  };

  const deleteQueriedAddress = async (payload: QueriedAddressPayload): Promise<QueriedAddresses> => {
    const response = await api.delete<QueriedAddresses>('/queried_addresses', {
      body: payload,
    });
    return QueriedAddressesSchema.parse(response);
  };

  return {
    addQueriedAddress,
    deleteQueriedAddress,
    queriedAddresses,
  };
}
