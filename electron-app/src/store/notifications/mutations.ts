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
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  reset(state: NotificationState) {
    state = Object.assign(state, defaultState());
  }
};
