import type { MessageHandler } from '../interfaces';
import type { ProgressUpdateResultData } from '../types/status-types';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';
import { SocketMessageProgressUpdateSubType } from '../types/base';
import { createCsvImportResultHandler } from './csv-import-result';

export function createProgressUpdateHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<ProgressUpdateResultData> {
  const { setUndecodedTransactionsStatus } = useDecodingStatusStore();
  const { setProtocolCacheStatus, setReceivingProtocolCacheStatus } = useProtocolCacheStatusStore();
  const { setHistoricalDailyPriceStatus, setHistoricalPriceStatus, setStatsPriceQueryStatus } = useHistoricCachePriceStore();
  const { reportProgress, reportProgressByPrefix } = useTaskOrchestrator();

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
        reportProgressByPrefix(
          { current: data.processed, total: data.total },
          ActivityKind.PRICES,
          ActivityPart.DAILY,
        );
        break;
      case SocketMessageProgressUpdateSubType.LIQUITY_STAKING_QUERY:
        reportProgress(
          makeActivityId(ActivityKind.LIQUITY, ActivityPart.STAKING),
          { current: data.processed, total: data.total },
        );
        break;
      case SocketMessageProgressUpdateSubType.STATS_PRICE_QUERY:
        setStatsPriceQueryStatus(data);
        break;
      case SocketMessageProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS:
        setHistoricalPriceStatus(data);
        break;
      case SocketMessageProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING:
        reportProgress(makeActivityId(ActivityKind.HISTORICAL_BALANCES), { current: data.processed, total: data.total });
        break;
    }

    return null;
  });
}
