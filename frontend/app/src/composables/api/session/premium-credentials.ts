import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import { type PremiumCapabilities, PremiumCapabilities as PremiumCapabilitiesSchema } from '@/modules/session/types';
import { logger } from '@/utils/logging';

interface UsePremiumCredentialsApiReturn {
  setPremiumCredentials: (username: string, apiKey: string, apiSecret: string) => Promise<true>;
  deletePremiumCredentials: () => Promise<true>;
  getPremiumCapabilities: () => Promise<PremiumCapabilities>;
}

function parsePremiumCapabilities(response: PremiumCapabilities): PremiumCapabilities {
  const result = PremiumCapabilitiesSchema.safeParse(response);
  if (result.success)
    return result.data;

  logger.warn('Premium capabilities parsing failed, attempting partial parse:', result.error.message);

  const sanitized: Record<string, unknown> = {};
  const shape = PremiumCapabilitiesSchema.shape;
  const raw: Record<string, unknown> = response;

  for (const [key, schema] of Object.entries(shape)) {
    if (!(key in raw))
      continue;

    const fieldResult = schema.safeParse(raw[key]);
    if (fieldResult.success) {
      sanitized[key] = fieldResult.data;
    }
    else {
      logger.warn(`Premium capabilities: dropping key "${key}" due to validation error:`, fieldResult.error.message);
    }
  }

  return PremiumCapabilitiesSchema.parse(sanitized);
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

    return parsePremiumCapabilities(response);
  };

  return {
    deletePremiumCredentials,
    getPremiumCapabilities,
    setPremiumCredentials,
  };
}
