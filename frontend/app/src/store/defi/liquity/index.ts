import {
  LiquityBalances,
  LiquityPoolDetails,
  LiquityStakingDetails,
  TroveEvents
} from '@rotki/common/lib/liquity';
import { type Ref } from 'vue';
import { type OnError } from '@/store/typing';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { fetchDataAsync } from '@/utils/fetch-async';
import { useLiquityApi } from '@/services/defi/liquity';

export const useLiquityStore = defineStore('defi/liquity', () => {
  const balances = ref<LiquityBalances>({}) as Ref<LiquityBalances>;
  const events = ref<TroveEvents>({}) as Ref<TroveEvents>;
  const staking = ref<LiquityStakingDetails>({}) as Ref<LiquityStakingDetails>;
  const stakingPools = ref<LiquityPoolDetails>({}) as Ref<LiquityPoolDetails>;

  const isPremium = usePremium();
  const { activeModules } = useModules();
  const { t, tc } = useI18n();
  const {
    fetchLiquityStakingPools,
    fetchLiquityBalances,
    fetchLiquityTroveEvents,
    fetchLiquityStaking
  } = useLiquityApi();

  const fetchPools = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: tc('actions.defi.liquity_pools.task.title')
    };

    const onError: OnError = {
      title: tc('actions.defi.liquity_pools.error.title'),
      error: message =>
        tc('actions.defi.liquity_pools.error.description', 0, {
          message
        })
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.LIQUITY_STAKING_POOLS,
          section: Section.DEFI_LIQUITY_STAKING_POOLS,
          meta,
          query: async () => await fetchLiquityStakingPools(),
          parser: result => LiquityPoolDetails.parse(result),
          onError
        },
        state: {
          isPremium,
          activeModules
        },
        requires: {
          premium: true,
          module: Module.LIQUITY
        },
        refresh
      },
      stakingPools
    );
  };

  const fetchBalances = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity.task.title').toString()
    };

    const onError: OnError = {
      title: t('actions.defi.liquity_balances.error.title').toString(),
      error: message =>
        t('actions.defi.liquity_balances.error.description', {
          message
        }).toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.LIQUITY_BALANCES,
          section: Section.DEFI_LIQUITY_BALANCES,
          meta,
          query: async () => await fetchLiquityBalances(),
          parser: result => LiquityBalances.parse(result),
          onError
        },
        state: {
          isPremium,
          activeModules
        },
        requires: {
          premium: false,
          module: Module.LIQUITY
        },
        refresh
      },
      balances
    );
  };

  const fetchEvents = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity_events.task.title').toString()
    };

    const onError: OnError = {
      title: t('actions.defi.liquity_events.error.title').toString(),
      error: message =>
        t('actions.defi.liquity_events.error.description', {
          message
        }).toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.LIQUITY_EVENTS,
          section: Section.DEFI_LIQUITY_EVENTS,
          meta,
          query: async () => await fetchLiquityTroveEvents(),
          parser: result => TroveEvents.parse(result),
          onError
        },
        state: {
          isPremium,
          activeModules
        },
        requires: {
          premium: true,
          module: Module.LIQUITY
        },

        refresh
      },
      events
    );
  };

  const fetchStaking = async (refresh = false): Promise<void> => {
    const meta: TaskMeta = {
      title: t('actions.defi.liquity_staking.task.title').toString()
    };

    const onError: OnError = {
      title: t('actions.defi.liquity_staking.error.title').toString(),
      error: message =>
        t('actions.defi.liquity_staking.error.description', {
          message
        }).toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.LIQUITY_STAKING,
          section: Section.DEFI_LIQUITY_STAKING,
          meta,
          query: async () => await fetchLiquityStaking(),
          parser: result => LiquityStakingDetails.parse(result),
          onError
        },
        state: {
          isPremium,
          activeModules
        },
        requires: {
          premium: true,
          module: Module.LIQUITY
        },
        refresh
      },
      staking
    );
  };

  const reset = (): void => {
    const { resetStatus } = useStatusUpdater(Section.DEFI_LIQUITY_BALANCES);

    set(balances, {});
    set(events, {});
    set(staking, {});

    resetStatus(Section.DEFI_LIQUITY_BALANCES);
    resetStatus(Section.DEFI_LIQUITY_EVENTS);
    resetStatus(Section.DEFI_LIQUITY_STAKING);
  };

  return {
    balances,
    events,
    staking,
    stakingPools,
    fetchBalances,
    fetchEvents,
    fetchStaking,
    fetchPools,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useLiquityStore, import.meta.hot));
}
