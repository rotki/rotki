import { type Watcher, WatcherType } from '@/types/session';

export const useWatchersStore = defineStore('session/watchers', () => {
  const watchers = ref<Watcher[]>([]);

  const { t } = useI18n();

  const loanWatchers = computed(() => {
    const loanWatcherTypes = [WatcherType];

    return get(watchers).filter(watcher =>
      loanWatcherTypes.includes(watcher.type)
    );
  });

  const { premium } = storeToRefs(usePremiumStore());
  const { notify } = useNotificationsStore();
  const api = useWatchersApi();

  const fetchWatchers = async (): Promise<void> => {
    if (!get(premium)) {
      return;
    }

    try {
      set(watchers, await api.watchers());
    } catch (e: any) {
      notify({
        title: t('actions.session.fetch_watchers.error.title').toString(),
        message: t('actions.session.fetch_watchers.error.message', {
          message: e.message
        }).toString(),
        display: true
      });
    }
  };

  const addWatchers = async (
    newWatchers: Omit<Watcher, 'identifier'>[]
  ): Promise<void> => {
    set(watchers, await api.addWatcher(newWatchers));
  };

  const deleteWatchers = async (identifiers: string[]): Promise<void> => {
    set(watchers, await api.deleteWatcher(identifiers));
  };

  const editWatchers = async (editedWatchers: Watcher[]): Promise<void> => {
    set(watchers, await api.editWatcher(editedWatchers));
  };

  return {
    watchers,
    loanWatchers,
    fetchWatchers,
    addWatchers,
    editWatchers,
    deleteWatchers
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useWatchersStore, import.meta.hot));
}
