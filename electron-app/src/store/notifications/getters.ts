import { GetterTree } from 'vuex';
import { NotificationState } from '@/store/notifications/state';
import { RotkehlchenState } from '@/store/store';

export const getters: GetterTree<NotificationState, RotkehlchenState> = {
  count(state: NotificationState): number {
    return state.data.length;
  },
  nextId(state: NotificationState): number {
    const ids = state.data.map(value => value.id).sort((a, b) => b - a);

    let nextId: number;
    if (ids.length > 0) {
      nextId = ids[0] + 1;
    } else {
      nextId = 1;
    }
    return nextId;
  }
};
