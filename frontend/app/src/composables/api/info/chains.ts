import type { ActionResult } from '@rotki/common';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';
import { EvmChainEntries, SupportedChains } from '@/types/api/chains';

interface UseSupportedChainsApiReturn {
  fetchSupportedChains: () => Promise<SupportedChains>;
  fetchAllEvmChains: () => Promise<EvmChainEntries>;
}

export function useSupportedChainsApi(): UseSupportedChainsApiReturn {
  const fetchSupportedChains = async (): Promise<SupportedChains> => {
    const response = await api.instance.get<ActionResult<SupportedChains>>(`/blockchains/supported`);
    return SupportedChains.parse(handleResponse(response));
  };

  const fetchAllEvmChains = async (): Promise<EvmChainEntries> => {
    const response = await api.instance.get<ActionResult<EvmChainEntries>>(`/blockchains/evm/all`);
    return EvmChainEntries.parse(handleResponse(response));
  };

  return {
    fetchAllEvmChains,
    fetchSupportedChains,
  };
}
