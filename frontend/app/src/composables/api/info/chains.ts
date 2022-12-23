import { type ActionResult } from '@rotki/common/lib/data';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';
import { type SupportedChains } from '@/types/api/chains';

export const useSupportedChainsApi = () => {
  const fetchSupportedChains = async () => {
    const response = await api.instance.get<ActionResult<SupportedChains>>(
      `/blockchains/supported`
    );
    return handleResponse(response);
  };

  return {
    fetchSupportedChains
  };
};
