import type { MessageHandler } from '../interfaces';
import type { ProgressUpdateResultData } from '../types/status-types';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { decodeActivity, decodeActivityId, type DecodeSubject } from '@/modules/history/events/tx/decode-activity';
import { protocolCacheActivity } from '@/modules/history/protocol-cache-activity';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { publishActivityDetail } from '@/modules/task-center/use-activity-detail';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';
import { SocketMessageProgressUpdateSubType } from '../types/base';
import { createCsvImportResultHandler } from './csv-import-result';

export function createProgressUpdateHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<ProgressUpdateResultData> {
  const { setUndecodedTransactionsStatus } = useDecodingStatusStore();
  const protocolCacheStore = useProtocolCacheStatusStore();
  const { setProtocolCacheStatus, setReceivingProtocolCacheStatus } = protocolCacheStore;
  const { setHistoricalDailyPriceStatus, setHistoricalPriceStatus, setStatsPriceQueryStatus } = useHistoricCachePriceStore();
  const { notifyHistoricalBalanceProcessingCompleted } = useDataIssuesInboxStore();
  const { reportProgress, reportProgressByPrefix, statusOf } = useTaskOrchestrator();
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
   * The activity a stats-price backfill is a phase of, by the counterparty naming it.
   *
   * The frames describe the historical-price lookups a staking statistics query makes on its way,
   * and the query's own activity is the only thing running while they arrive. A counterparty with
   * no entry reports nothing rather than guessing at an id: the backend can name one before the
   * frontend has an activity for it, and a wrong id would caption unrelated work.
   */
  const statsPriceActivities = new Map<string, ActivityId>([
    ['kraken', makeActivityId(ActivityKind.STAKING, ActivityPart.KRAKEN)],
    ['liquity', makeActivityId(ActivityKind.LIQUITY, ActivityPart.STATISTICS)],
  ]);

  /**
   * The decode variant currently running for a chain, if either is.
   *
   * A chain's cached and forced decodes are separate activities, and only one of the pair can be
   * live. Publishing to both instead would leave an entry against an id with no record, which
   * nothing ever drops: the channel is cleaned up by the orchestrator, and it can only clean up
   * what it has a record for.
   */
  function liveDecodeSubject(chain: string): DecodeSubject | undefined {
    return [{ chain, ignoreCache: false }, { chain, ignoreCache: true }]
      .find(subject => statusOf(ActivityKind.TX_DECODING, ...decodeActivity.partsOf(subject)).running);
  }

  /**
   * Attach the protocol-cache rows to whatever work is filling them.
   *
   * Two producers send the same frames: the user's cache refresh, which has an activity of its own,
   * and decoding, which fills a cache when a decoder reaches a log that needs one. Read back from
   * the store so the rows are the accumulated set rather than the single pair this frame carries.
   *
   * Published only against a live record, and nothing at all when neither is running — which is
   * every frame today that arrives outside both, and is what the panel already shows for them.
   */
  function publishProtocolCacheDetail(data: { chain: string }): void {
    const protocols = protocolCacheStore.protocolCacheStatus;

    if (statusOf(ActivityKind.PROTOCOL_CACHE).running)
      publishActivityDetail(protocolCacheActivity, undefined, { protocols });

    const chain = matchChain(data.chain) ?? data.chain.toLowerCase();
    const decoding = liveDecodeSubject(chain);
    if (decoding !== undefined) {
      publishActivityDetail(decodeActivity, decoding, {
        protocols: protocols.filter(row => (matchChain(row.chain) ?? row.chain.toLowerCase()) === chain),
      });
    }
  }

  /**
   * Report a stats-price backfill onto the staking query it is a phase of.
   *
   * A counterparty with no activity of its own reports nothing rather than falling back to some
   * broader id: the frames are about that one query, and driving anything else with its counts
   * would caption unrelated work.
   */
  function reportStatsPriceProgress(data: { counterparty: string; processed: number; total: number }): void {
    const activity = statsPriceActivities.get(data.counterparty);
    if (activity !== undefined)
      reportProgress(activity, { current: data.processed, total: data.total });
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
        publishProtocolCacheDetail(data);
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
        reportStatsPriceProgress(data);
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
