import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { Section, Status } from '@/store/const';
import {
  dexTradeNumericKeys,
  uniswapEventsNumericKeys,
  uniswapNumericKeys
} from '@/store/defi/const';
import { SushiswapMutations } from '@/store/defi/sushiswap/mutation-types';
import { SushiswapState } from '@/store/defi/sushiswap/types';
import { RotkehlchenState } from '@/store/types';
import { fetchAsync, setStatus } from '@/store/utils';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const actions: ActionTree<SushiswapState, RotkehlchenState> = {
  async fetchBalances(context, refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.sushiswap_balances.task.title').toString(),
      numericKeys: uniswapNumericKeys
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchSushiswapBalances(),
      mutation: SushiswapMutations.SET_BALANCES,
      taskType: TaskType.SUSHISWAP_BALANCES,
      section: Section.DEFI_SUSHISWAP_BALANCES,
      module: Module.SUSHISWAP,
      meta: meta,
      refresh,
      checkPremium: true,
      onError: {
        title: i18n.t('actions.defi.sushiswap_balances.error.title').toString(),
        error: message =>
          i18n
            .t('actions.defi.sushiswap_balances.error.description', {
              message
            })
            .toString()
      }
    });

    await context.dispatch('balances/fetchSupportedAssets', true, {
      root: true
    });
  },

  async fetchTrades(context, refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.sushiswap_trades.task.title').toString(),
      numericKeys: dexTradeNumericKeys
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchSushiswapTrades(),
      mutation: SushiswapMutations.SET_TRADES,
      taskType: TaskType.SUSHISWAP_TRADES,
      section: Section.DEFI_SUSHISWAP_TRADES,
      module: Module.SUSHISWAP,
      meta: meta,
      refresh,
      checkPremium: true,
      onError: {
        title: i18n.t('actions.defi.sushiswap_trades.error.title').toString(),
        error: message =>
          i18n
            .t('actions.defi.sushiswap_trades.error.description', {
              message
            })
            .toString()
      }
    });

    await context.dispatch('balances/fetchSupportedAssets', true, {
      root: true
    });
  },

  async fetchEvents(context, refresh: boolean = false) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.sushiswap_events.task.title').toString(),
      numericKeys: uniswapEventsNumericKeys
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchSushiswapEvents(),
      mutation: SushiswapMutations.SET_EVENTS,
      taskType: TaskType.SUSHISWAP_EVENTS,
      section: Section.DEFI_SUSHISWAP_EVENTS,
      module: Module.SUSHISWAP,
      meta: meta,
      refresh,
      checkPremium: true,
      onError: {
        title: i18n.t('actions.defi.sushiswap_events.error.title').toString(),
        error: message =>
          i18n
            .t('actions.defi.sushiswap_events.error.description', {
              message
            })
            .toString()
      }
    });

    await context.dispatch('balances/fetchSupportedAssets', true, {
      root: true
    });
  },
  async purge({ commit, rootGetters: { status } }) {
    function resetStatus(section: Section) {
      setStatus(Status.NONE, section, status, commit);
    }

    commit(SushiswapMutations.SET_BALANCES, {});
    commit(SushiswapMutations.SET_EVENTS, {});
    resetStatus(Section.DEFI_SUSHISWAP_BALANCES);
    resetStatus(Section.DEFI_SUSHISWAP_EVENTS);
  }
};
