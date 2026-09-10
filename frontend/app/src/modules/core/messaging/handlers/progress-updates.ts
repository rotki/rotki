import type { MessageHandler } from '../interfaces';
import type { ProgressUpdateResultData } from '../types/status-types';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { decodeActivityId } from '@/modules/history/events/tx/decode-activity';
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
  const { notifyHistoricalBalanceProcessingCompleted } = useDataIssuesInboxStore();
  const { reportProgress, reportProgressByPrefix } = useTaskOrchestrator();
  const { matchChain } = useSupportedChains();

  /**
   * Report a chain's decode progress onto the chain-wide decode activity.
   *
   * Two exact ids rather than a prefix over the chain: a prefix would also match
   * `targetedDecodeActivityId`, whose denominator is the transactions that request named, not the
   * chain's undecoded count. Only one of the two can be running for a chain, and `reportProgress`
   * ignores an id that is not, so the pair is a single report either way.
   *
   * The chain is canonicalised first. The decoder reports `ChainID.to_name()` ('ethereum') while
   * the activity carries the chain id its flow submitted ('eth'), so the raw value matches nothing
   * and the decode would sit at zero for the whole run.
   */
  function reportDecodeProgress(data: { chain: string; processed: number; total: number }): void {
    const chain = matchChain(data.chain) ?? data.chain.toLowerCase();
    const steps = { current: data.processed, total: data.total };
    reportProgress(decodeActivityId(chain, false), steps);
    reportProgress(decodeActivityId(chain, true), steps);
  }

  /**
   * Report a multi-pair historical price query onto the batch price activities.
   *
   * `ActivityPart.BATCH` belongs to the prefix. The producer is the multi-pair query behind
   * `PRICES:HISTORIC:BATCH:<n>`, so a prefix stopping at `HISTORIC` would also drive the
   * single-pair `PRICES:HISTORIC:<from>:<to>:<ts>` activities, which this frame's counts describe
   * nothing about.
   */
  function reportBatchPriceProgress(data: { processed: number; total: number }): void {
    reportProgressByPrefix(
      { current: data.processed, total: data.total },
      ActivityKind.PRICES,
      ActivityPart.HISTORIC,
      ActivityPart.BATCH,
    );
  }

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
        reportDecodeProgress(data);
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
          makeActivityId(ActivityKind.LIQUITY, ActivityPart.STAKE),
          { current: data.processed, total: data.total },
        );
        break;
      case SocketMessageProgressUpdateSubType.STATS_PRICE_QUERY:
        setStatsPriceQueryStatus(data);
        break;
      case SocketMessageProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS:
        setHistoricalPriceStatus(data);
        reportBatchPriceProgress(data);
        break;
      case SocketMessageProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING:
        reportProgress(makeActivityId(ActivityKind.HISTORICAL_BALANCES), { current: data.processed, total: data.total });
        if (data.processed >= data.total)
          notifyHistoricalBalanceProcessingCompleted();
        break;
    }

    return null;
  });
}
