import { type BigNumber } from '@rotki/common';
import isEqual from 'lodash/isEqual';
import { type Ref } from 'vue';
import { useNftBalanceApi } from '@/services/balances/nft';
import { type Collection } from '@/types/collection';
import { Module } from '@/types/modules';
import {
  type NonFungibleBalance,
  NonFungibleBalancesCollectionResponse,
  type NonFungibleBalancesRequestPayload
} from '@/types/nfbalances';
import { Section, Status } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';
import {
  defaultCollectionState,
  mapCollectionResponse
} from '@/utils/collection';
import { logger } from '@/utils/logging';

export const useNonFungibleBalancesStore = defineStore(
  'balances/non-fungible',
  () => {
    const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

    const defaultRequestPayload =
      (): Partial<NonFungibleBalancesRequestPayload> => {
        return {
          offset: 0,
          limit: get(itemsPerPage),
          ignoredAssetsHandling: 'exclude'
        };
      };

    const requestPayload: Ref<Partial<NonFungibleBalancesRequestPayload>> = ref(
      defaultRequestPayload()
    );

    const balances: Ref<Collection<NonFungibleBalance>> = ref(
      defaultCollectionState<NonFungibleBalance>()
    );

    const nonFungibleTotalValue = ref<BigNumber>(Zero);

    const { activeModules } = storeToRefs(useGeneralSettingsStore());
    const { awaitTask, isTaskRunning } = useTaskStore();
    const { notify } = useNotificationsStore();
    const { tc } = useI18n();

    const updateRequestPayload = async (
      payload: Partial<NonFungibleBalancesRequestPayload>
    ) => {
      if (!isEqual(payload, get(requestPayload))) {
        set(requestPayload, payload);
        await fetchNonFungibleBalances();
      }
    };

    const { fetchNfBalances, fetchNfBalancesTask } = useNftBalanceApi();

    const fetchNonFungibleBalances = async (refresh = false) => {
      if (!get(activeModules).includes(Module.NFTS)) {
        return;
      }
      const { setStatus, loading, isFirstLoad, resetStatus } = useStatusUpdater(
        Section.NON_FUNGIBLE_BALANCES
      );
      const taskType = TaskType.NF_BALANCES;

      const fetchNfBalancesHandler = async (
        onlyCache: boolean,
        parameters?: Partial<NonFungibleBalancesRequestPayload>
      ) => {
        const defaults: NonFungibleBalancesRequestPayload = {
          limit: 0,
          offset: 0,
          ascending: [true],
          orderByAttributes: ['name'],
          ignoreCache: !onlyCache
        };

        const payload: NonFungibleBalancesRequestPayload = Object.assign(
          defaults,
          parameters ?? get(requestPayload)
        );

        if (onlyCache) {
          const result = await fetchNfBalances(payload);
          if (
            !payload.ignoredAssetsHandling ||
            payload.ignoredAssetsHandling === 'exclude'
          ) {
            set(nonFungibleTotalValue, result.totalUsdValue);
          }
          return mapCollectionResponse(result);
        }

        const { taskId } = await fetchNfBalancesTask(payload);
        const { result } = await awaitTask<
          NonFungibleBalancesCollectionResponse,
          TaskMeta
        >(taskId, taskType, {
          title: tc('actions.nft_balances.task.title')
        });

        setStatus(
          get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
        );

        const parsedResult =
          NonFungibleBalancesCollectionResponse.parse(result);

        return mapCollectionResponse(parsedResult);
      };

      try {
        const firstLoad = isFirstLoad();
        const onlyCache = !(refresh || firstLoad);
        if ((get(isTaskRunning(taskType)) || loading()) && !onlyCache) {
          return;
        }

        const fetchOnlyCache = async (): Promise<void> => {
          set(balances, await fetchNfBalancesHandler(true));
        };

        setStatus(firstLoad ? Status.LOADING : Status.REFRESHING);

        await fetchOnlyCache();

        if (!onlyCache) {
          setStatus(Status.REFRESHING);
          await fetchNfBalancesHandler(false);
          await fetchOnlyCache();
        }

        setStatus(
          get(isTaskRunning(taskType)) ? Status.REFRESHING : Status.LOADED
        );
      } catch (e: any) {
        logger.error(e);
        notify({
          title: tc('actions.nft_balances.error.title'),
          message: tc('actions.nft_balances.error.message', 0, {
            message: e.message
          }),
          display: true
        });
        resetStatus();
      }
    };

    return {
      balances,
      nonFungibleTotalValue,
      updateRequestPayload,
      fetchNonFungibleBalances
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useNonFungibleBalancesStore, import.meta.hot)
  );
}
