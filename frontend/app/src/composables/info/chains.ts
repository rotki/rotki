import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';

export const useSupportedChains = () => {
  const { fetchSupportedChains } = useSupportedChainsApi();

  const supportedChains = asyncComputed(() => fetchSupportedChains(), []);
  const isEvm = (chain: MaybeRef<Blockchain>) =>
    computed(() => {
      const blockchain = get(chain);
      const match = get(supportedChains).find(x => x.name === blockchain);
      return match && match.type === 'evm';
    });

  return {
    isEvm
  };
};
