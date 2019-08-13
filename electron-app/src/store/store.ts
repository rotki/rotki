import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { notifications } from '@/store/notifications';
import { balances } from '@/store/balances';
import { tasks } from '@/store/tasks';
import { session } from '@/store/session';
import { reports } from '@/store/reports';

Vue.use(Vuex);

const emptyMessage = (): Message => ({
  title: '',
  description: '',
  success: false
});

const store: StoreOptions<RotkehlchenState> = {
  state: {
    message: emptyMessage()
  },
  mutations: {
    setMessage: (state: RotkehlchenState, message: Message) => {
      state.message = message;
    },
    resetMessage: (state: RotkehlchenState) => {
      state.message = emptyMessage();
    }
  },
  actions: {},
  getters: {},
  modules: {
    notifications,
    balances,
    tasks,
    session,
    reports
  }
};
export default new Vuex.Store(store);

export interface RotkehlchenState {
  message: Message;
}

export interface Message {
  readonly title: string;
  readonly description: string;
  readonly success: boolean;
}
