import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import {
  SUPPORTED_EXCHANGES,
  type SupportedExchange,
  type SupportedExternalExchanges
} from '@/types/exchanges';
import { Module } from '@/types/modules';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES,
  ALL_TRANSACTIONS,
  type Purgeable
} from '@/types/session/purge';

export const useSessionPurgeStore = defineStore('session/purge', () => {
  const { purgeExchange, purgeTransactions } = usePurgeStore();
  const { resetState } = useDefiStore();
  const { reset } = useStakingStore();

  const purgeCache = async (purgeable: Purgeable): Promise<void> => {
    if (purgeable === ALL_CENTRALIZED_EXCHANGES) {
      await purgeExchange(ALL_CENTRALIZED_EXCHANGES);
    } else if (purgeable === ALL_DECENTRALIZED_EXCHANGES) {
      resetState(ALL_DECENTRALIZED_EXCHANGES);
    } else if (purgeable === ALL_MODULES) {
      reset();
      resetState(ALL_MODULES);
    } else if (
      SUPPORTED_EXCHANGES.includes(purgeable as SupportedExchange) ||
      EXTERNAL_EXCHANGES.includes(purgeable as SupportedExternalExchanges)
    ) {
      await purgeExchange(purgeable as SupportedExchange);
    } else if (purgeable === ALL_TRANSACTIONS) {
      await purgeTransactions();
    } else if (Object.values(Module).includes(purgeable as Module)) {
      if ([Module.ETH2].includes(purgeable as Module)) {
        reset(purgeable as Module);
      } else {
        resetState(purgeable as Module);
      }
    }
  };

  return {
    purgeCache
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useSessionPurgeStore, import.meta.hot)
  );
}
