import { api } from '@/modules/api/rotki-api';
import { EvmChainEntries, SupportedChains } from '@/types/api/chains';

interface UseSupportedChainsApiReturn {
  fetchSupportedChains: () => Promise<SupportedChains>;
  fetchAllEvmChains: () => Promise<EvmChainEntries>;
}

export function useSupportedChainsApi(): UseSupportedChainsApiReturn {
  const fetchSupportedChains = async (): Promise<SupportedChains> => {
    const response = await api.get<SupportedChains>('/blockchains/supported');
    return SupportedChains.parse(response);
  };

  const fetchAllEvmChains = async (): Promise<EvmChainEntries> => {
    const response = await api.get<EvmChainEntries>('/blockchains/evm/all');
    return EvmChainEntries.parse(response);
  };

  return {
    fetchAllEvmChains,
    fetchSupportedChains,
  };
}
