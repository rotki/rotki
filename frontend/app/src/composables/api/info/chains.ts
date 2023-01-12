import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';
import { SupportedChains } from '@/types/api/chains';

export const useSupportedChainsApi = () => {
  const fetchSupportedChains = async (): Promise<SupportedChains> => {
    const response = await api.instance.get<ActionResult<SupportedChains>>(
      `/blockchains/supported`
    );
    return SupportedChains.parse(handleResponse(response));
  };

  return {
    fetchSupportedChains
  };
};
