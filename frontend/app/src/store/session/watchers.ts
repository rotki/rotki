import { type Watcher, WatcherType } from '@/types/session';
import { useNotificationsStore } from '@/store/notifications';
import { useWatchersApi } from '@/composables/api/session/watchers';
import { usePremium } from '@/composables/premium';

export const useWatchersStore = defineStore('session/watchers', () => {
  const watchers = ref<Watcher[]>([]);
  const monitorWatchers = ref<boolean>(true);

  const { t } = useI18n();

  const loanWatchers = computed(() => {
    const loanWatcherTypes = [WatcherType];

    return get(watchers).filter(watcher => loanWatcherTypes.includes(watcher.type));
  });

  const premium = usePremium();
  const { notify } = useNotificationsStore();
  const api = useWatchersApi();

  const fetchWatchers = async (): Promise<void> => {
    if (!get(premium) || !get(monitorWatchers))
      return;

    try {
      set(watchers, await api.watchers());
      set(monitorWatchers, get(watchers).length > 0);
    }
    catch (error: any) {
      notify({
        display: true,
        message: t('actions.session.fetch_watchers.error.message', {
          message: error.message,
        }),
        title: t('actions.session.fetch_watchers.error.title'),
      });
    }
  };

  const addWatchers = async (newWatchers: Omit<Watcher, 'identifier'>[]): Promise<void> => {
    set(watchers, await api.addWatcher(newWatchers));
    set(monitorWatchers, get(watchers).length > 0);
  };

  const deleteWatchers = async (identifiers: string[]): Promise<void> => {
    set(watchers, await api.deleteWatcher(identifiers));
    set(monitorWatchers, get(watchers).length > 0);
  };

  const editWatchers = async (editedWatchers: Watcher[]): Promise<void> => {
    set(watchers, await api.editWatcher(editedWatchers));
  };

  return {
    addWatchers,
    deleteWatchers,
    editWatchers,
    fetchWatchers,
    loanWatchers,
    watchers,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useWatchersStore, import.meta.hot));
