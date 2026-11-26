import type { useI18n } from 'vue-i18n';
import type { MessageHandler } from '../interfaces';
import type { ProgressUpdateResultData } from '../types/status-types';
import { createConditionalHandler } from '@/modules/core/messaging/utils';
import { useHistoricalBalancesProgress } from '@/modules/history/balances/use-historical-balances-progress';
import { useDataIssueRemediationStore } from '@/modules/history/data-issues/use-data-issue-remediation-store';
import { useStakingQueryProgress } from '@/modules/staking/use-staking-query-progress';
import { SocketMessageProgressUpdateSubType } from '../types/base';
import { createCsvImportResultHandler } from './csv-import-result';
import { createDecodeProgressHandlers } from './progress-updates-decode';
import { createPriceProgressHandlers } from './progress-updates-prices';

export function createProgressUpdateHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<ProgressUpdateResultData> {
  const { handleProtocolCacheUpdates, handleUndecodedTransactions } = createDecodeProgressHandlers();
  const { handleDailyPrices, handleMultiplePrices, handleStatsPrices } = createPriceProgressHandlers();
  const { notifyRemediationCompleted } = useDataIssueRemediationStore();
  const { reportHistoricalBalancesProgress } = useHistoricalBalancesProgress();
  const { isStakingQueryProgress, reportStakingQueryProgress } = useStakingQueryProgress();

  /**
   * Record the end of a periodic auto-remediation run.
   *
   * Only the completed phase changes anything: a run that has just started has not resolved or
   * re-stated an issue yet, so the inbox has nothing new to read on it.
   */
  function handleRemediationPhase(data: { phase: 'running' | 'completed' }): void {
    if (data.phase === 'completed')
      notifyRemediationCompleted();
  }

  return createConditionalHandler<ProgressUpdateResultData>(async (data) => {
    if (isStakingQueryProgress(data)) {
      reportStakingQueryProgress(data);
      return null;
    }

    const subtype = data.subtype;

    if (subtype === SocketMessageProgressUpdateSubType.CSV_IMPORT_RESULT) {
      const csvHandler = createCsvImportResultHandler(t);
      return csvHandler.handle(data);
    }

    switch (subtype) {
      case SocketMessageProgressUpdateSubType.DATA_ISSUE_REMEDIATION:
        handleRemediationPhase(data);
        break;
      case SocketMessageProgressUpdateSubType.UNDECODED_TRANSACTIONS:
        handleUndecodedTransactions(data);
        break;
      case SocketMessageProgressUpdateSubType.PROTOCOL_CACHE_UPDATES:
        handleProtocolCacheUpdates(data);
        break;
      case SocketMessageProgressUpdateSubType.HISTORICAL_PRICE_QUERY_STATUS:
        handleDailyPrices(data);
        break;
      case SocketMessageProgressUpdateSubType.STATS_PRICE_QUERY:
        handleStatsPrices(data);
        break;
      case SocketMessageProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS:
        handleMultiplePrices(data);
        break;
      case SocketMessageProgressUpdateSubType.HISTORICAL_BALANCE_PROCESSING:
        reportHistoricalBalancesProgress(data);
        break;
    }

    return null;
  });
}
