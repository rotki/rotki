import { LiquityBalances, TroveEvents } from '@rotki/common/lib/liquity';
import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { api } from '@/services/rotkehlchen-api';
import { Module } from '@/services/session/consts';
import { Section, Status } from '@/store/const';
import { LiquityMutations } from '@/store/defi/liquity/mutation-types';
import { LiquitityState } from '@/store/defi/liquity/types';
import { RotkehlchenState } from '@/store/types';
import { fetchAsync, setStatus } from '@/store/utils';

export const actions: ActionTree<LiquitityState, RotkehlchenState> = {
  async fetchBalances(context, refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.liquity.task.title').toString(),
      ignoreResult: false,
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
      ignoreResult: false,
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
  }
};
