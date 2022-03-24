import {
  LiquityBalances,
  LiquityStaking,
  LiquityStakingEvents,
  TroveEvents
} from '@rotki/common/lib/liquity';
import { Ref, ref } from '@vue/composition-api';
import { set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { getPremium, setupModuleEnabled } from '@/composables/session';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { Section } from '@/store/const';
import { OnError } from '@/store/typing';
import { fetchDataAsync, getStatusUpdater } from '@/store/utils';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const useLiquityStore = defineStore('defi/liquity', () => {
  const balances = ref<LiquityBalances>({}) as Ref<LiquityBalances>;
  const events = ref<TroveEvents>({}) as Ref<TroveEvents>;
  const staking = ref<LiquityStaking>({}) as Ref<LiquityStaking>;
  const stakingEvents = ref<LiquityStakingEvents>(
    {}
  ) as Ref<LiquityStakingEvents>;

  const isPremium = getPremium();
  const { activeModules } = setupModuleEnabled();

  async function fetchBalances(refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.liquity.task.title').toString(),
      numericKeys: []
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.liquity_balances.error.title').toString(),
      error: message =>
        i18n
          .t('actions.defi.liquity_balances.error.description', {
            message
          })
          .toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.LIQUITY_BALANCES,
          section: Section.DEFI_LIQUITY_BALANCES,
          meta,
          query: async () => await api.defi.fetchLiquityBalances(),
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
  }

  async function fetchEvents(refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.liquity_events.task.title').toString(),
      numericKeys: []
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.liquity_events.error.title').toString(),
      error: message =>
        i18n
          .t('actions.defi.liquity_events.error.description', {
            message
          })
          .toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.LIQUITY_EVENTS,
          section: Section.DEFI_LIQUITY_EVENTS,
          meta,
          query: async () => await api.defi.fetchLiquityTroveEvents(),
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
  }

  async function purge() {
    const { resetStatus } = getStatusUpdater(Section.DEFI_LIQUITY_BALANCES);

    set(balances, {});
    set(events, {});

    resetStatus();
    resetStatus(Section.DEFI_LIQUITY_EVENTS);
  }

  async function fetchStaking(refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.liquity_staking.task.title').toString(),
      numericKeys: []
    };

    const onError: OnError = {
      title: i18n.t('actions.defi.liquity_staking.error.title').toString(),
      error: message =>
        i18n
          .t('actions.defi.liquity_staking.error.description', {
            message
          })
          .toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.LIQUITY_STAKING,
          section: Section.DEFI_LIQUITY_STAKING,
          meta,
          query: async () => await api.defi.fetchLiquityStaking(),
          parser: result => LiquityStaking.parse(result),
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
  }

  async function fetchStakingEvents(refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n
        .t('actions.defi.liquity_staking_events.task.title')
        .toString(),
      numericKeys: []
    };

    const onError: OnError = {
      title: i18n
        .t('actions.defi.liquity_staking_events.error.title')
        .toString(),
      error: message =>
        i18n
          .t('actions.defi.liquity_staking_events.error.description', {
            message
          })
          .toString()
    };

    await fetchDataAsync(
      {
        task: {
          type: TaskType.LIQUITY_STAKING_EVENTS,
          section: Section.DEFI_LIQUITY_STAKING_EVENTS,
          meta,
          query: async () => await api.defi.fetchLiquityStakingEvents(),
          parser: result => LiquityStakingEvents.parse(result),
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
      stakingEvents
    );
  }

  async function clearStaking() {
    const { resetStatus } = getStatusUpdater(Section.DEFI_LIQUITY_STAKING);
    set(staking, {});
    set(stakingEvents, {});
    resetStatus();
    resetStatus(Section.DEFI_LIQUITY_STAKING_EVENTS);
  }

  const reset = () => {
    set(balances, {});
    set(events, {});
    set(staking, {});
    set(stakingEvents, {});
  };

  return {
    balances,
    events,
    staking,
    stakingEvents,
    fetchBalances,
    fetchEvents,
    fetchStaking,
    fetchStakingEvents,
    clearStaking,
    purge,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useLiquityStore, import.meta.hot));
}
