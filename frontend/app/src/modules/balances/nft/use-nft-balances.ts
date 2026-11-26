import type { MaybeRef } from 'vue';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/modules/balances/types/nfbalances';
import type { Collection } from '@/modules/core/common/collection';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { pipe } from 'plainfp';
import { map, type ResultAsync } from 'plainfp/result-async';
import { useNftBalancesApi } from '@/modules/balances/api/use-nft-balances-api';
import { nftBalancesActivity } from '@/modules/balances/balances.activity';
import { useNftBalancesSync } from '@/modules/balances/nft/use-nft-balances-sync';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { fromRequest, type RequestError } from '@/modules/core/api/request-result';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';
import { logger } from '@/modules/core/common/logging/logging';
import { Module } from '@/modules/core/common/modules';
import { useSetting } from '@/modules/settings/use-setting';
import { shouldSkipFetch } from '@/modules/task-center/core/status';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface NftBalancesReturn {
  fetchNonFungibleBalances: (payload: MaybeRef<NonFungibleBalancesRequestPayload>) => ResultAsync<Collection<NonFungibleBalance>, RequestError>;
  refreshNonFungibleBalances: (userInitiated?: boolean) => Promise<void>;
}

export function useNftBalances(): NftBalancesReturn {
  const activeModules = useSetting('activeModules');
  const { nonFungibleTotalValue } = storeToRefs(useBalancesStore());
  const { statusOf } = useNativeTask();
  const { fetchNfBalances } = useNftBalancesApi();
  const { syncNonFungibleBalances } = useNftBalancesSync();

  const fetchNonFungibleBalances = async (
    payload: MaybeRef<NonFungibleBalancesRequestPayload>,
  ): ResultAsync<Collection<NonFungibleBalance>, RequestError> => {
    const payloadVal = get(payload);

    return pipe(
      fromRequest(async () => fetchNfBalances(payloadVal)),
      map((response) => {
        if (!payloadVal.ignoredAssetsHandling || payloadVal.ignoredAssetsHandling === 'exclude')
          set(nonFungibleTotalValue, response.totalValue);

        return mapCollectionResponse(response);
      }),
    );
  };

  /**
   * Refreshes the non-fungible balances, an expensive query.
   *
   * @remarks
   * Skipped while the NFT module is off, while a run is in flight, and, unless the user asked,
   * once it has loaded. See {@link useNftBalancesSync} for what makes it stale.
   */
  const refreshNonFungibleBalances = async (userInitiated = false): Promise<void> => {
    if (!get(activeModules).includes(Module.NFTS))
      return;

    const status = statusOf(nftBalancesActivity.kind);
    if (shouldSkipFetch(status, userInitiated)) {
      logger.info('skipping non fungible balances refresh');
      return;
    }

    await syncNonFungibleBalances();
  };

  return {
    fetchNonFungibleBalances,
    refreshNonFungibleBalances,
  };
}
