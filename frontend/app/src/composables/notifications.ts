import { NotificationData } from '@rotki/common/lib/messages';
import { useNotifications } from '@/store/notifications';

export const setupNotifications = () => {
  const store = useNotifications();
  const count = computed(() => store.count);
  const queue = computed<NotificationData[]>(() => store.queue);
  const data = computed(() => store.data);

  const remove = (id: number) => store.remove(id);
  const reset = () => store.reset();
  const displayed = async (ids: number[]) => store.displayed(ids);

  return {
    data,
    queue,
    count,
    remove,
    reset,
    displayed
  };
};
