import { type SupportedExchange } from '@/types/exchanges';
import { Section } from '@/types/status';
import { ALL_CENTRALIZED_EXCHANGES } from '@/types/session/purge';

export const usePurgeStore = defineStore('history/purge', () => {
  const purgeExchange = async (
    exchange: SupportedExchange | typeof ALL_CENTRALIZED_EXCHANGES
  ): Promise<void> => {
    const { resetStatus } = useStatusUpdater(Section.TRADES);

    if (exchange === ALL_CENTRALIZED_EXCHANGES) {
      resetStatus();
      resetStatus(Section.ASSET_MOVEMENT);
      resetStatus(Section.LEDGER_ACTIONS);
    }
  };

  const purgeTransactions = async (): Promise<void> => {
    const { resetStatus } = useStatusUpdater(Section.TX);
    resetStatus();
  };

  return {
    purgeExchange,
    purgeTransactions
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(usePurgeStore, import.meta.hot));
}
