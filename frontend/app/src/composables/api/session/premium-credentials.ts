import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import { type PremiumCapabilities, PremiumCapabilities as PremiumCapabilitiesSchema } from '@/types/session';

interface UsePremiumCredentialsApiReturn {
  setPremiumCredentials: (username: string, apiKey: string, apiSecret: string) => Promise<true>;
  deletePremiumCredentials: () => Promise<true>;
  getPremiumCapabilities: () => Promise<PremiumCapabilities>;
}

export function usePremiumCredentialsApi(): UsePremiumCredentialsApiReturn {
  const setPremiumCredentials = async (username: string, apiKey: string, apiSecret: string): Promise<true> => api.patch<true>(
    `/users/${username}`,
    {
      premiumApiKey: apiKey,
      premiumApiSecret: apiSecret,
    },
  );

  const deletePremiumCredentials = async (): Promise<true> => api.delete<true>('/premium');

  const getPremiumCapabilities = async (): Promise<PremiumCapabilities> => {
    const response = await api.get<PremiumCapabilities>('/premium/capabilities', {
      validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
    });

    return PremiumCapabilitiesSchema.parse(response);
  };

  return {
    deletePremiumCredentials,
    getPremiumCapabilities,
    setPremiumCredentials,
  };
}
