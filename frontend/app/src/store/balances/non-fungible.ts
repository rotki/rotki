import { BigNumber } from '@rotki/common';
import { ComputedRef, Ref } from 'vue';
import { useStatusUpdater } from '@/composables/status';
import { bigNumberSum } from '@/filters';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { Module } from '@/types/modules';
import { NonFungibleBalance, NonFungibleBalances } from '@/types/nfbalances';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

export const useNonFungibleBalancesStore = defineStore(
  'balances/non-fungible',
  () => {
    const balances: Ref<NonFungibleBalances> = ref({});

    const { activeModules } = storeToRefs(useGeneralSettingsStore());
    const { awaitTask } = useTasks();
    const { notify } = useNotifications();
    const { tc } = useI18n();

    const nonFungibleBalances: ComputedRef<NonFungibleBalance[]> = computed(
      () => {
        const data: NonFungibleBalance[] = [];
        const nonFungibleBalances = get(balances) as NonFungibleBalances;
        for (const address in nonFungibleBalances) {
          const addressNfBalance = nonFungibleBalances[address];
          data.push(...addressNfBalance);
        }
        return data;
      }
    );

    const nonFungibleTotalValue = (
      includeLPToken: boolean = false
    ): ComputedRef<BigNumber> =>
      computed(() => {
        return bigNumberSum(
          get(nonFungibleBalances)
            .filter(item => includeLPToken || !item.isLp)
            .map(item => item.usdPrice)
        );
      });

    const fetchNonFungibleBalances = async (payload?: {
      ignoreCache: boolean;
    }): Promise<void> => {
      if (!get(activeModules).includes(Module.NFTS)) {
        return;
      }
      const { isFirstLoad, setStatus, resetStatus } = useStatusUpdater(
        Section.NON_FUNGIBLE_BALANCES
      );
      try {
        setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);
        const taskType = TaskType.NF_BALANCES;
        const { taskId } = await api.balances.fetchNfBalances(payload);
        const { result } = await awaitTask<NonFungibleBalances, TaskMeta>(
          taskId,
          taskType,
          {
            title: tc('actions.nft_balances.task.title'),
            numericKeys: []
          }
        );

        set(balances, NonFungibleBalances.parse(result));
        setStatus(Status.LOADED);
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

    const reset = (): void => {
      set(balances, {});
    };

    return {
      balances,
      nonFungibleBalances,
      nonFungibleTotalValue,
      fetchNonFungibleBalances,
      reset
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useNonFungibleBalancesStore, import.meta.hot)
  );
}
