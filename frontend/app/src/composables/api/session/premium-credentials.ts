import type { ActionResult } from '@rotki/common';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validAuthorizedStatus, validStatus, validWithParamsSessionAndExternalService } from '@/services/utils';
import { type PremiumCapabilities, PremiumCapabilities as PremiumCapabilitiesSchema } from '@/types/session';

interface UsePremiumCredentialsApiReturn {
  setPremiumCredentials: (username: string, apiKey: string, apiSecret: string) => Promise<true>;
  deletePremiumCredentials: () => Promise<true>;
  getPremiumCapabilities: () => Promise<PremiumCapabilities>;
}

export function usePremiumCredentialsApi(): UsePremiumCredentialsApiReturn {
  const setPremiumCredentials = async (username: string, apiKey: string, apiSecret: string): Promise<true> => {
    const response = await api.instance.patch<ActionResult<true>>(
      `/users/${username}`,
      {
        premium_api_key: apiKey,
        premium_api_secret: apiSecret,
      },
      { validateStatus: validAuthorizedStatus },
    );

    return handleResponse(response);
  };

  const deletePremiumCredentials = async (): Promise<true> => {
    const response = await api.instance.delete<ActionResult<true>>('/premium', {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const getPremiumCapabilities = async (): Promise<PremiumCapabilities> => {
    const response = await api.instance.get<ActionResult<PremiumCapabilities>>('/premium/capabilities', {
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return PremiumCapabilitiesSchema.parse(handleResponse(response));
  };

  return {
    deletePremiumCredentials,
    getPremiumCapabilities,
    setPremiumCredentials,
  };
}
