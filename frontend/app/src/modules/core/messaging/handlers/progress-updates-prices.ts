import type { CommonQueryStatusData } from '@rotki/common';
import type { StatsPriceQueryData } from '@/modules/core/messaging/types/status-types';
import { dailyPricesActivity, historicPriceBatchActivity } from '@/modules/assets/prices/prices.activity';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { liquityActivity } from '@/modules/staking/liquity/liquity.activity';
import { krakenStakingActivity } from '@/modules/staking/staking.activity';
import { type ActivityId, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface PriceProgressHandlers {
  /** Records a daily historical price query's status and reports it onto the daily price activities. */
  handleDailyPrices: (data: CommonQueryStatusData) => void;
  /** Records a multi-pair historical price query's status and reports it onto the batch price activities. */
  handleMultiplePrices: (data: CommonQueryStatusData) => void;
  /** Records a stats-price backfill's status and reports it onto the staking query it is a phase of. */
  handleStatsPrices: (data: StatsPriceQueryData) => void;
}

/**
 * The progress-update handlers for historical price queries: the daily prices, the multi-pair
 * batches, and the stats-price backfills a staking statistics query makes.
 */
export function createPriceProgressHandlers(): PriceProgressHandlers {
  const { setHistoricalDailyPriceStatus, setHistoricalPriceStatus, setStatsPriceQueryStatus } = useHistoricCachePriceStore();
  const { reportProgress, reportProgressByPrefix } = useTaskOrchestrator();

  /**
   * The activity a stats-price backfill is a phase of, by the counterparty naming it.
   *
   * The frames describe the historical-price lookups a staking statistics query makes on its way,
   * and the query's own activity is the only thing running while they arrive. A counterparty with
   * no entry reports nothing rather than guessing at an id: the backend can name one before the
   * frontend has an activity for it, and a wrong id would caption unrelated work.
   */
  const statsPriceActivities = new Map<string, ActivityId>([
    ['kraken', krakenStakingActivity.id()],
    ['liquity', liquityActivity.id({ part: ActivityPart.STATISTICS })],
  ]);

  function handleDailyPrices(data: CommonQueryStatusData): void {
    setHistoricalDailyPriceStatus(data);
    reportProgressByPrefix(
      { current: data.processed, total: data.total },
      dailyPricesActivity.kind,
      ...dailyPricesActivity.partsWithin([]),
    );
  }

  /**
   * Report a stats-price backfill onto the staking query it is a phase of.
   *
   * A counterparty with no activity of its own reports nothing rather than falling back to some
   * broader id: the frames are about that one query, and driving anything else with its counts
   * would caption unrelated work.
   */
  function handleStatsPrices(data: StatsPriceQueryData): void {
    setStatsPriceQueryStatus(data);
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
  function handleMultiplePrices(data: CommonQueryStatusData): void {
    setHistoricalPriceStatus(data);
    reportProgressByPrefix(
      { current: data.processed, total: data.total },
      historicPriceBatchActivity.kind,
      ...historicPriceBatchActivity.partsWithin([ActivityPart.BATCH]),
    );
  }

  return {
    handleDailyPrices,
    handleMultiplePrices,
    handleStatsPrices,
  };
}
