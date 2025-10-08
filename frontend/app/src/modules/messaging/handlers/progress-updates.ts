import type { MessageHandler } from '../interfaces';
import type { ProgressUpdateResultData } from '../types/status-types';
import { createConditionalHandler } from '@/modules/messaging/utils';
import { useLiquityStore } from '@/store/defi/liquity';
import { useHistoryStore } from '@/store/history';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { SocketMessageProgressUpdateSubType } from '../types/base';
import { createCsvImportResultHandler } from './csv-import-result';

export function createProgressUpdateHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<ProgressUpdateResultData> {
  // Capture store methods at handler creation time (in setup context)
  const { setProtocolCacheStatus, setUndecodedTransactionsStatus } = useHistoryStore();
  const { setHistoricalDailyPriceStatus, setHistoricalPriceStatus, setStatsPriceQueryStatus } = useHistoricCachePriceStore();
  const { setStakingQueryStatus } = useLiquityStore();

  return createConditionalHandler<ProgressUpdateResultData>(async (data) => {
    const subtype = data.subtype;

    if (subtype === SocketMessageProgressUpdateSubType.CSV_IMPORT_RESULT) {
      const csvHandler = createCsvImportResultHandler(t);
      return csvHandler.handle(data);
    }

    switch (subtype) {
      case SocketMessageProgressUpdateSubType.UNDECODED_TRANSACTIONS:
        setUndecodedTransactionsStatus(data);
        break;
      case SocketMessageProgressUpdateSubType.PROTOCOL_CACHE_UPDATES:
        setProtocolCacheStatus(data);
        break;
      case SocketMessageProgressUpdateSubType.HISTORICAL_PRICE_QUERY_STATUS:
        setHistoricalDailyPriceStatus(data);
        break;
      case SocketMessageProgressUpdateSubType.LIQUITY_STAKING_QUERY:
        setStakingQueryStatus(data);
        break;
      case SocketMessageProgressUpdateSubType.STATS_PRICE_QUERY:
        setStatsPriceQueryStatus(data);
        break;
      case SocketMessageProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS:
        setHistoricalPriceStatus(data);
        break;
    }

    return null;
  });
}
