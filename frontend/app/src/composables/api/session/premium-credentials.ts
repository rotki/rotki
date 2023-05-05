import { type ActionResult } from '@rotki/common/lib/data';
import {
  handleResponse,
  validAuthorizedStatus,
  validStatus
} from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';

export const usePremiumCredentialsApi = () => {
  const setPremiumCredentials = async (
    username: string,
    apiKey: string,
    apiSecret: string
  ): Promise<true> => {
    const response = await api.instance.patch<ActionResult<true>>(
      `/users/${username}`,
      {
        premium_api_key: apiKey,
        premium_api_secret: apiSecret
      },
      { validateStatus: validAuthorizedStatus }
    );

    return handleResponse(response);
  };

  const deletePremiumCredentials = async (): Promise<true> => {
    const response = await api.instance.delete<ActionResult<true>>('/premium', {
      validateStatus: validStatus
    });

    return handleResponse(response);
  };

  return {
    setPremiumCredentials,
    deletePremiumCredentials
  };
};
