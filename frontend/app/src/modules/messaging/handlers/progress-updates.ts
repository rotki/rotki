import type { MessageHandler } from '../interfaces';
import type { ProgressUpdateResultData } from '../types/status-types';
import { useLiquityStore } from '@/modules/defi/use-liquity-store';
import { useHistoricalBalancesStore } from '@/modules/history/balances/store';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import { createConditionalHandler } from '@/modules/messaging/utils';
import { useHistoricCachePriceStore } from '@/modules/prices/use-historic-cache-price-store';
import { SocketMessageProgressUpdateSubType } from '../types/base';
import { createCsvImportResultHandler } from './csv-import-result';

export function createProgressUpdateHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<ProgressUpdateResultData> {
  const { setUndecodedTransactionsStatus } = useDecodingStatusStore();
  const { setProtocolCacheStatus, setReceivingProtocolCacheStatus } = useProtocolCacheStatusStore();
  const { setHistoricalDailyPriceStatus, setHistoricalPriceStatus, setStatsPriceQueryStatus } = useHistoricCachePriceStore();
  const { setStakingQueryStatus } = useLiquityStore();
  const { setProcessingProgress } = useHistoricalBalancesStore();

  return createConditionalHandler<ProgressUpdateResultData>(async (data) => {
    const subtype = data.subtype;

    if (subtype === SocketMessageProgressUpdateSubType.CSV_IMPORT_RESULT) {
      const csvHandler = createCsvImportResultHandler(t);
      return csvHandler.handle(data);
    }

    switch (subtype) {
      case SocketMessageProgressUpdateSubType.UNDECODED_TRANSACTIONS:
        setReceivingProtocolCacheStatus(false);
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
      case SocketMessageProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING:
        setProcessingProgress(data);
        break;
    }

    return null;
  });
}
