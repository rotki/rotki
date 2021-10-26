import { computed } from '@vue/composition-api';
import { NotificationData } from '@/store/notifications/types';
import { useStore } from '@/store/utils';

export const setupNotifications = () => {
  const store = useStore();
  const count = computed(() => store.getters['notifications/count']);
  const data = computed(() => store.state.notifications!!.data);
  const remove = (id: number) => {
    store.commit('notifications/remove', id);
  };

  const reset = () => {
    store.commit('notifications/reset');
  };

  const displayed = async (id: number[]) => {
    await store.dispatch('notifications/displayed', id);
  };

  const queue = computed<NotificationData[]>(
    () => store.getters['notifications/queue']
  );

  return {
    data,
    queue,
    count,
    remove,
    reset,
    displayed
  };
};
