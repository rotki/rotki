import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import {
  type QueriedAddressPayload,
  type QueriedAddresses
} from '@/services/session/types';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';

export const useQueriedAddressApi = () => {
  const queriedAddresses = async (): Promise<QueriedAddresses> =>
    api.instance
      .get<ActionResult<QueriedAddresses>>('/queried_addresses', {
        validateStatus: validWithSessionStatus
      })
      .then(handleResponse);

  const addQueriedAddress = async (
    payload: QueriedAddressPayload
  ): Promise<QueriedAddresses> =>
    api.instance
      .put<ActionResult<QueriedAddresses>>('/queried_addresses', payload, {
        validateStatus: validStatus
      })
      .then(handleResponse);

  const deleteQueriedAddress = async (
    payload: QueriedAddressPayload
  ): Promise<QueriedAddresses> =>
    api.instance
      .delete<ActionResult<QueriedAddresses>>('/queried_addresses', {
        data: payload,
        validateStatus: validStatus
      })
      .then(handleResponse);

  return {
    queriedAddresses,
    addQueriedAddress,
    deleteQueriedAddress
  };
};
