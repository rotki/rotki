import {
  LiquityBalances,
  LiquityStaking,
  LiquityStakingEvents,
  TroveEvents
} from '@rotki/common/lib/liquity';
import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { Section, Status } from '@/store/const';
import { LiquityMutations } from '@/store/defi/liquity/mutation-types';
import { LiquityState } from '@/store/defi/liquity/types';
import { RotkehlchenState } from '@/store/types';
import { fetchAsync, setStatus } from '@/store/utils';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const actions: ActionTree<LiquityState, RotkehlchenState> = {
  async fetchBalances(context, refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.liquity.task.title').toString(),
      numericKeys: []
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchLiquityBalances(),
      mutation: LiquityMutations.SET_BALANCES,
      taskType: TaskType.LIQUITY_BALANCES,
      section: Section.DEFI_LIQUITY_BALANCES,
      module: Module.LIQUITY,
      meta: meta,
      refresh,
      checkPremium: false,
      parser: result => LiquityBalances.parse(result),
      onError: {
        title: i18n.t('actions.defi.liquity_balances.error.title').toString(),
        error: message =>
          i18n
            .t('actions.defi.liquity_balances.error.description', {
              message
            })
            .toString()
      }
    });
  },

  async fetchEvents(context, refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.liquity_events.task.title').toString(),
      numericKeys: []
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchLiquityTroveEvents(),
      mutation: LiquityMutations.SET_EVENTS,
      taskType: TaskType.LIQUITY_EVENTS,
      section: Section.DEFI_LIQUITY_EVENTS,
      module: Module.LIQUITY,
      meta: meta,
      refresh,
      checkPremium: true,
      parser: result => TroveEvents.parse(result),
      onError: {
        title: i18n.t('actions.defi.liquity_events.error.title').toString(),
        error: message =>
          i18n
            .t('actions.defi.liquity_events.error.description', {
              message
            })
            .toString()
      }
    });
  },
  async purge({ commit, rootGetters: { status } }) {
    function resetStatus(section: Section) {
      setStatus(Status.NONE, section, status, commit);
    }

    commit(LiquityMutations.SET_BALANCES, {});
    commit(LiquityMutations.SET_EVENTS, {});
    resetStatus(Section.DEFI_LIQUITY_BALANCES);
    resetStatus(Section.DEFI_LIQUITY_EVENTS);
  },
  async fetchStaking(context, refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.liquity_staking.task.title').toString(),
      numericKeys: []
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchLiquityStaking(),
      mutation: LiquityMutations.SET_STAKING,
      taskType: TaskType.LIQUITY_STAKING,
      section: Section.DEFI_LIQUITY_STAKING,
      module: Module.LIQUITY,
      meta: meta,
      refresh,
      checkPremium: true,
      parser: result => LiquityStaking.parse(result),
      onError: {
        title: i18n.t('actions.defi.liquity_staking.error.title').toString(),
        error: message =>
          i18n
            .t('actions.defi.liquity_staking.error.description', {
              message
            })
            .toString()
      }
    });
  },
  async fetchStakingEvents(context, refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n
        .t('actions.defi.liquity_staking_events.task.title')
        .toString(),
      numericKeys: []
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchLiquityStakingEvents(),
      mutation: LiquityMutations.SET_STAKING_EVENTS,
      taskType: TaskType.LIQUITY_STAKING_EVENTS,
      section: Section.DEFI_LIQUITY_STAKING_EVENTS,
      module: Module.LIQUITY,
      meta: meta,
      refresh,
      checkPremium: true,
      parser: result => LiquityStakingEvents.parse(result),
      onError: {
        title: i18n
          .t('actions.defi.liquity_staking_events.error.title')
          .toString(),
        error: message =>
          i18n
            .t('actions.defi.liquity_staking_events.error.description', {
              message
            })
            .toString()
      }
    });
  },
  async clearStaking({ commit, rootGetters: { status } }) {
    function resetStatus(section: Section) {
      setStatus(Status.NONE, section, status, commit);
    }

    commit(LiquityMutations.SET_STAKING, {});
    commit(LiquityMutations.SET_STAKING_EVENTS, {});
    resetStatus(Section.DEFI_LIQUITY_STAKING);
    resetStatus(Section.DEFI_LIQUITY_STAKING_EVENTS);
  }
};
