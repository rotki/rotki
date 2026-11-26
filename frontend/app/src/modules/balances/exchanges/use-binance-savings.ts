import type { ResultAsync } from 'plainfp/result-async';
import type { MaybeRef } from 'vue';
import type { ExchangeSavingsCollection, ExchangeSavingsRequestPayload } from '@/modules/balances/types/exchanges';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { pipe } from 'plainfp';
import { filter, unique } from 'plainfp/arrays';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { exchangeSavingsActivity } from '@/modules/balances/balances.activity';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useExchangeSavingsSync } from '@/modules/balances/exchanges/use-exchange-savings-sync';
import { fromRequest, type RequestError } from '@/modules/core/api/request-result';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { logger } from '@/modules/core/common/logging/logging';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseBinanceSavingsReturn {
  fetchExchangeSavings: (payload: MaybeRef<ExchangeSavingsRequestPayload>) => ResultAsync<ExchangeSavingsCollection, RequestError>;
  refreshExchangeSavings: (userInitiated?: boolean) => Promise<void>;
}

/** Only binance exposes a savings/interest history. */
const SAVINGS_LOCATIONS: ReadonlySet<string> = new Set(['binance', 'binanceus']);

/**
 * Whether a refresh should actually run (the functional restatement of the old `fetchDisabled`):
 * never while a sync is in flight, and automatically (non user-initiated) only before the first
 * successful load.
 */
function shouldRefresh(status: WorkStatus, userInitiated: boolean): boolean {
  return !status.active && (userInitiated || !status.everCompleted);
}

export function useBinanceSavings(): UseBinanceSavingsReturn {
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { useWorkStatus } = useTaskCenter();
  const { getExchangeSavings } = useExchangeApi();
  const { syncExchangeSavings } = useExchangeSavingsSync();

  const savingsStatus = useWorkStatus(exchangeSavingsActivity.kind);

  const fetchExchangeSavings = async (
    payload: MaybeRef<ExchangeSavingsRequestPayload>,
  ): ResultAsync<ExchangeSavingsCollection, RequestError> => fromRequest(async () => mapCollectionResponse(
    await getExchangeSavings({
      ...get(payload),
      onlyCache: true,
    }),
  ));

  const savingsLocations = (): string[] => pipe(
    get(connectedExchanges).map(({ location }) => location),
    unique,
    filter(location => SAVINGS_LOCATIONS.has(location)),
  );

  const refreshExchangeSavings = async (userInitiated = false): Promise<void> => {
    if (!shouldRefresh(get(savingsStatus), userInitiated)) {
      logger.info('skipping exchanges savings');
      return;
    }

    await Promise.all(savingsLocations().map(syncExchangeSavings));
  };

  return {
    fetchExchangeSavings,
    refreshExchangeSavings,
  };
}
