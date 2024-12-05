import { type Watcher, WatcherType } from '@/types/session';
import { useNotificationsStore } from '@/store/notifications';

export const useWatchersStore = defineStore('session/watchers', () => {
  const watchers = ref<Watcher[]>([]);

  const { t } = useI18n();

  const loanWatchers = computed(() => {
    const loanWatcherTypes = [WatcherType];

    return get(watchers).filter(watcher => loanWatcherTypes.includes(watcher.type));
  });

  const premium = usePremium();
  const { notify } = useNotificationsStore();
  const api = useWatchersApi();

  const fetchWatchers = async (): Promise<void> => {
    if (!get(premium))
      return;

    try {
      set(watchers, await api.watchers());
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
  };

  const deleteWatchers = async (identifiers: string[]): Promise<void> => {
    set(watchers, await api.deleteWatcher(identifiers));
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
