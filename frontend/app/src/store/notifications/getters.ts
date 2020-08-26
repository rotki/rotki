import { GetterTree } from 'vuex';
import { NotificationState } from '@/store/notifications/state';
import { NotificationData } from '@/store/notifications/types';
import { RotkehlchenState } from '@/store/types';

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
  },
  queue(state: NotificationState): NotificationData[] {
    return state.data.filter(notification => notification.display);
  }
};
