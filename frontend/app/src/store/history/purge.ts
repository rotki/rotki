import { useStatusUpdater } from '@/composables/status';
import { ALL_CENTRALIZED_EXCHANGES } from '@/services/session/consts';
import { useAssetMovements } from '@/store/history/asset-movements';
import { useLedgerActions } from '@/store/history/ledger-actions';
import { useTrades } from '@/store/history/trades';
import { SupportedExchange } from '@/types/exchanges';
import { Section } from '@/types/status';

export const usePurgeStore = defineStore('history/purge', () => {
  const { fetchTrades } = useTrades();
  const { fetchAssetMovements } = useAssetMovements();
  const { fetchLedgerActions } = useLedgerActions();
  const purgeHistoryLocation = async (exchange: SupportedExchange) => {
    await Promise.allSettled([
      fetchTrades(true, exchange),
      fetchAssetMovements(true, exchange),
      fetchLedgerActions(true, exchange)
    ]);
  };

  const purgeExchange = async (
    exchange: SupportedExchange | typeof ALL_CENTRALIZED_EXCHANGES
  ) => {
    const { resetStatus } = useStatusUpdater(Section.TRADES);

    if (exchange === ALL_CENTRALIZED_EXCHANGES) {
      resetStatus();
      resetStatus(Section.ASSET_MOVEMENT);
      resetStatus(Section.LEDGER_ACTIONS);
    } else {
      await purgeHistoryLocation(exchange);
    }
  };

  return {
    purgeExchange,
    purgeHistoryLocation
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(usePurgeStore, import.meta.hot));
}
