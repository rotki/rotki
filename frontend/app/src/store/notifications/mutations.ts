import { MutationTree } from 'vuex';
import { defaultState, NotificationState } from '@/store/notifications/state';
import { NotificationData } from '@/typing/types';

export const mutations: MutationTree<NotificationState> = {
  update(state: NotificationState, payload: NotificationData[]) {
    state.data = [...state.data, ...payload];
  },

  remove(state: NotificationState, id: number) {
    const notifications = [...state.data];

    const index = notifications.findIndex(v => v.id === id);
    if (index > -1) {
      notifications.splice(index, 1);
    }

    state.data = notifications;
  },

  notifications(state: NotificationState, data: NotificationData[]) {
    state.data = data;
  },

  reset(state: NotificationState) {
    Object.assign(state, defaultState());
  }
};
