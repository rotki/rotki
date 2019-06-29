import { MutationTree } from 'vuex';
import { NotificationState } from '@/notifications/state';
import { NotificationData } from '@/typing/types';

export const mutations: MutationTree<NotificationState> = {
  update(state: NotificationState, payload: NotificationData[]) {
    state.data = [...state.data, ...payload];
  },
  clear(state: NotificationState) {
    state.data = [];
  },
  remove(state: NotificationState, id: number) {
    const notifications = [...state.data];

    const index = notifications.findIndex(v => v.id === id);
    if (index > -1) {
      notifications.splice(index, 1);
    }

    state.data = notifications;
  }
};
