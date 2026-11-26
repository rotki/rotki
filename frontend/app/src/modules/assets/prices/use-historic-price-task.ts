import { type BigNumber, One } from '@rotki/common';
import { getOr, map as mapResult, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { type HistoricPricePayload, HistoricPrices } from '@/modules/assets/prices/price-types';
import { historicPriceActivity } from '@/modules/assets/prices/prices.activity';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { convertFromTimestamp } from '@/modules/core/common/data/date';
import { logger } from '@/modules/core/common/logging/logging';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseHistoricPriceTaskReturn {
  /**
   * The price of `fromAsset` in `toAsset` at `timestamp`.
   *
   * @returns One when both assets are the same, and minus one when the price is unknown or the
   * query failed.
   */
  getHistoricPrice: (payload: HistoricPricePayload) => Promise<BigNumber>;
}

export function useHistoricPriceTask(): UseHistoricPriceTaskReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { submitTask } = useNativeTask();
  const { queryHistoricalRate } = usePriceApi();

  const getHistoricPrice = async (payload: HistoricPricePayload): Promise<BigNumber> => {
    const { fromAsset, timestamp, toAsset } = payload;
    if (fromAsset === toAsset) {
      return One;
    }

    const outcome = await submitTask<BigNumber>({
      id: historicPriceActivity.id(payload),
      kind: historicPriceActivity.kind,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<BigNumber, TaskError>> => mapResult(
        await runTask<HistoricPrices>(
          async () => queryHistoricalRate(fromAsset, toAsset, timestamp),
        ),
        result => HistoricPrices.parse(result).assets[fromAsset]?.[timestamp] ?? One.negated(),
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.historic'), { date: convertFromTimestamp(timestamp), fromAsset, toAsset }),
      title: t('task_center.group.prices'),
    });

    onActionableError(outcome, error => logger.error(error.message));

    return getOr(outcome, One.negated());
  };

  return {
    getHistoricPrice,
  };
}
